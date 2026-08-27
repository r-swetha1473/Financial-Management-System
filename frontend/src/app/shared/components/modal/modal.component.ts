import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-modal',
  standalone: true,
  template: `
    @if (open) {
      <div class="modal-backdrop" (click)="closed.emit()">
        <div class="modal" [class.modal--narrow]="narrow" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <div class="modal__header">
            <h3>{{ title }}</h3>
            <button class="btn btn--ghost btn--sm" type="button" (click)="closed.emit()">Close</button>
          </div>
          <div class="modal__body">
            <ng-content />
          </div>
          <div class="modal__footer">
            <ng-content select="[modal-footer]" />
          </div>
        </div>
      </div>
    }
  `,
})
export class ModalComponent {
  @Input() open = false;
  @Input() title = '';
  @Input() narrow = false;
  @Output() closed = new EventEmitter<void>();
}
