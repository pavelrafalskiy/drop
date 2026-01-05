import logging
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools import format_datetime, index_exists

_logger = logging.getLogger(__name__)


class WorkoutEvent(models.Model):
    _name = "workout.event"
    _description = "Workout Event"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_time desc"

    NOTIF_WINDOW_PAST = 15
    NOTIF_WINDOW_FUTURE = 30
    NOTIF_ETA_OFFSET = 10

    _JOB_IDENTITY_PREFIX = "workout_notify"
    _JOB_ONGOING_STATES = ["pending", "enqueued", "waiting", "failed", "started"]
    _JOB_REMOVABLE_STATES = ["pending", "enqueued", "waiting", "failed"]

    name = fields.Char(
        string="Workout Name",
        required=True,
        tracking=True,
    )
    start_time = fields.Datetime(
        string="Start Time",
        required=True,
        tracking=True,
    )
    is_notification_sent = fields.Boolean(
        string="Notification Sent",
        default=False,
        tracking=True,
        copy=False,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
    )

    @api.private
    def init(self):
        super().init()
        index_name = "workout_event_is_notif_sent_false_idx"
        if not index_exists(self._cr, index_name):
            _logger.info("Creating partial index %s", index_name)
            self._cr.execute(
                f"""
                CREATE INDEX {index_name}
                ON {self._table} (start_time)
                WHERE is_notification_sent IS FALSE
                """
            )

    def _register_hook(self):
        patched_method = self._patch_job_auto_delay(
            "action_send_notification",
            context_key="auto_delay_notify",
        )
        self._patch_method("action_send_notification", patched_method)
        return super()._register_hook()

    @api.model
    def _get_notification_time_window(self):
        now = fields.Datetime.now()
        return (
            now - timedelta(minutes=self.NOTIF_WINDOW_PAST),
            now + timedelta(minutes=self.NOTIF_WINDOW_FUTURE),
        )

    def _get_notification_eta(self):
        self.ensure_one()
        return max(
            self.start_time - timedelta(minutes=self.NOTIF_ETA_OFFSET),
            fields.Datetime.now(),
        )

    def _get_job_identity_key(self):
        self.ensure_one()
        return f"{self._JOB_IDENTITY_PREFIX}_{self.id}"

    def action_send_notification_job_options(self):
        self.ensure_one()
        return {
            "priority": 5,
            "max_retries": 6,
            "identity_key": self._get_job_identity_key(),
            "description": f"Notification for {self.name}",
            "eta": self._get_notification_eta(),
        }

    def action_send_notification(self):
        self.ensure_one()
        if self.is_notification_sent:
            return

        start_bound, end_bound = self._get_notification_time_window()
        if self.start_time > end_bound or self.start_time < start_bound:
            _logger.info(
                "Skipping notification for '%s': out of time window.", self.name
            )
            return

        target_user = self.user_id or self.env.ref(
            "base.user_admin",
            raise_if_not_found=False,
        )
        if not target_user:
            return

        user_tz = target_user.tz or self.env.context.get("tz") or "UTC"
        display_time = format_datetime(
            self.env,
            self.start_time,
            tz=user_tz,
            dt_format="HH:mm",
        )
        message_body = Markup(
            _("🔔 <b>Reminder:</b> Your workout '%s' starts soon at %s.")
        ) % (self.name, display_time)

        self.message_post(
            body=message_body,
            subtype_xmlid="mail.mt_comment",
        )

        workout_date = fields.Date.context_today(self, timestamp=self.start_time)

        self.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=workout_date,
            summary=_("Workout: %s") % self.name,
            note=_("Starts at %s") % display_time,
            user_id=target_user.id,
        )
        self.is_notification_sent = True

    def _schedule_notification_safe(self, force_recreate=False):
        self.mapped("user_id")

        identity_map = {r._get_job_identity_key(): r for r in self}

        existing_jobs = self.env["queue.job"].search(
            [
                ("identity_key", "in", list(identity_map.keys())),
                ("state", "in", self._JOB_ONGOING_STATES),
            ]
        )

        jobs_by_key = {j.identity_key: j for j in existing_jobs}

        for record in self:
            key = record._get_job_identity_key()
            job = jobs_by_key.get(key)

            if job:
                failed_job = job.filtered(lambda j: j.state == "failed")
                pending_job = job.filtered(lambda j: j.state == "pending")

                if failed_job and force_recreate:
                    failed_job.unlink()
                elif pending_job:
                    new_eta = record._get_notification_eta()
                    if pending_job.eta != new_eta:
                        pending_job.write({"eta": new_eta})
                    continue
                else:
                    continue

            recipient_lang = record.user_id.lang or self.env.user.lang or "en_US"
            record.with_context(
                auto_delay_notify=True, lang=recipient_lang
            ).action_send_notification()

    @api.model
    def cron_check_upcoming_workouts(self):
        start_window, end_window = self._get_notification_time_window()

        workouts = self.search(
            [
                ("start_time", ">=", start_window),
                ("start_time", "<=", end_window),
                ("is_notification_sent", "=", False),
            ]
        )
        workouts._schedule_notification_safe()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._schedule_notification_safe()
        return records

    def write(self, vals):
        if "start_time" in vals:
            vals["is_notification_sent"] = False
        res = super().write(vals)
        if "start_time" in vals:
            self._schedule_notification_safe(force_recreate=True)
        return res

    def unlink(self):
        identity_keys = [r._get_job_identity_key() for r in self]
        jobs = self.env["queue.job"].search(
            [
                ("identity_key", "in", identity_keys),
                ("state", "in", self._JOB_REMOVABLE_STATES),
            ]
        )
        if jobs:
            jobs.unlink()
        return super().unlink()
