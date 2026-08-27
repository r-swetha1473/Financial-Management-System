import { Component, EventEmitter, Input, Output } from '@angular/core';

import { ModalComponent } from '../modal/modal.component';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  template: `
    <app-modal [open]="open" [title]="title" [narrow]="true" (closed)="cancelled.emit()">
      <p class="text-secondary">{{ message }}</p>
      <div modal-footer>
        <button class="btn btn--secondary" type="button" (click)="cancelled.emit()">Cancel</button>
        <button class="btn" [class]="confirmClass" type="button" [disabled]="busy" (click)="confirmed.emit()">
          {{ confirmLabel }}
        </button>
      </div>
    </app-modal>
  `,
  imports: [ModalComponent],
})
export class ConfirmDialogComponent {
  @Input() open = false;
  @Input() title = 'Confirm';
  @Input() message = '';
  @Input() confirmLabel = 'Confirm';
  @Input() confirmClass = 'btn--primary';
  @Input() busy = false;
  @Output() confirmed = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();
}
