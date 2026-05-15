import { Component, ElementRef, input, model, output, signal, viewChild } from "@angular/core";


@Component({
    standalone: true,
    selector: 'app-modal',
    templateUrl: './modal.html',
})
export class Modal {
    private dialogRef = viewChild.required<ElementRef<HTMLDialogElement>>('dialog');
    header = input.required<string>();
    label = input.required<string>();
    submitButtonText = input<string>("Add");
    isCancelButton = input<boolean>(true);
    modalTriggerStyling = input<string>();
    inputValue = model<string>();
    submitted = output<string>();

    submit() {
        // When `submitButtonText` button is clicked emit value from the
        // text field into the function specified in the parent component
        this.submitted.emit(this.inputValue() ?? '');
        this.inputValue.set('');

        this.dialogRef().nativeElement.close();
    }

}