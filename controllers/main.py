from urllib.parse import urlparse
from odoo.addons.web.controllers.home import Home
from odoo.http import request


class HomeCustomRedirect(Home):

    def _login_redirect(self, uid, redirect=None):
        url = super()._login_redirect(uid, redirect=redirect)

        parsed_url = urlparse(url)
        clean_path = parsed_url.path.rstrip("/").lower()

        if clean_path == "/odoo":
            user = request.env["res.users"].sudo().browse(uid)
            if user.has_group("base.group_system"):
                return "/odoo/settings"

        return url
