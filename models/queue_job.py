from odoo import models


class QueueJob(models.Model):
    _inherit = "queue.job"

    def action_workout_view(self):
        self.ensure_one()
        records = self.records
        if not records or records._name != "workout.event":
            return self.related_action_open_record()

        return {
            "type": "ir.actions.act_window",
            "res_model": "workout.event",
            "res_id": records.id,
            "view_mode": "form",
            "target": "current",
        }
