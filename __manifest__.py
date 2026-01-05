{
    "name": "Project 2",
    "version": "18.0.1.0.0",
    "category": "Web",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "web",
        "queue_job",
        "queue_job_cron",
        "queue_job_cron_jobrunner",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "data/workout_data.xml",
        "views/workout_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "drop/static/src/js/save_confirmation.js",
            "drop/static/src/js/x2many_dialog_patch.js",
            "drop/static/src/js/x2many_dialog_buttons.xml",
        ],
    },
    "installable": True,
    "application": False,
}
