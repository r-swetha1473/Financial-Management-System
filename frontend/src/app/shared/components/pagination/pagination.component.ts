import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-pagination',
  standalone: true,
  template: `
    <div class="pagination">
      <span>Showing {{ from }}–{{ to }} of {{ total }}</span>
      <div class="pagination__buttons">
        <button class="btn btn--secondary btn--sm" type="button" [disabled]="page <= 1" (click)="pageChange.emit(page - 1)">
          Previous
        </button>
        <button class="btn btn--secondary btn--sm" type="button" [disabled]="page >= totalPages" (click)="pageChange.emit(page + 1)">
          Next
        </button>
      </div>
    </div>
  `,
})
export class PaginationComponent {
  @Input() page = 1;
  @Input() pageSize = 10;
  @Input() total = 0;
  @Output() pageChange = new EventEmitter<number>();

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  get from(): number {
    return this.total === 0 ? 0 : (this.page - 1) * this.pageSize + 1;
  }

  get to(): number {
    return Math.min(this.total, this.page * this.pageSize);
  }
}
