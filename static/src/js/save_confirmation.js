import { patch } from "@web/core/utils/patch";
import { X2ManyFieldDialog } from "@web/views/fields/relational_utils";
import { Record } from "@web/model/relational_model/record";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export const saveConfirmationTitle = _t("Save Confirmation");
export const saveConfirmationMessage = _t("You are about to apply the changes.\n\nAre you sure all data is correct?");
export const confirmLabel = _t("Confirm and Save");
export const cancelLabel = _t("Cancel and Discard");

/**
 * @param {Object} dialogService
 * @returns {Promise<boolean>}
 */
async function askConfirmation(dialogService) {
    return new Promise((resolve) => {
        dialogService.add(ConfirmationDialog, {
            title: saveConfirmationTitle,
            body: saveConfirmationMessage,
            confirmLabel: confirmLabel,
            cancelLabel: cancelLabel,
            confirm: () => resolve(true),
            cancel: () => resolve(false),
        });
    });
}

patch(X2ManyFieldDialog.prototype, {
    async save(params) {
        const isValid = await this.record.checkValidity({ displayNotification: true });
        if (!isValid) {
            return false;
        }
        const confirmed = await askConfirmation(this.env.services.dialog);
        if (confirmed) {
            await this.props.save(this.record);
            if (!params?.saveAndNew) {
                this.props.close();
            }
            return true;
        } else {
            await this.record.discard();
            return false;
        }
    },
});

patch(Record.prototype, {
    async urgentSave() {
        return false;
    },

    async save() {
        if (this._isConfirming || this.model._urgentSave) {
            return false;
        }
        await this.model._askChanges();
        if (!this.dirty && !this.isNew) {
            return super.save(...arguments);
        }
        const isValid = await this.checkValidity({ displayNotification: true });
        if (!isValid) {
            return false;
        }
        try {
            this._isConfirming = true;
            const confirmed = await askConfirmation(this.model.dialog);
            if (confirmed) {
                return await super.save(...arguments);
            } else {
                await this.discard();
                return false;
            }
        } finally {
            this._isConfirming = false;
        }
    },
});
