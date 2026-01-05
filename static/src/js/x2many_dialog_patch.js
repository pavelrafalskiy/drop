import { patch } from "@web/core/utils/patch";
import { X2ManyFieldDialog } from "@web/views/fields/relational_utils";

patch(X2ManyFieldDialog.prototype, {
    async saveAndNew() {
        return this.save({ saveAndNew: false });
    },
});