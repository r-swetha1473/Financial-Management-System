import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  template: `<span class="badge" [class]="toneClass">{{ label }}</span>`,
})
export class StatusBadgeComponent {
  @Input({ required: true }) status = '';

  get label(): string {
    return this.status.replaceAll('_', ' ');
  }

  get toneClass(): string {
    const value = this.status.toLowerCase();
    if (['paid', 'approved', 'active', 'completed', 'delivered', 'issued', 'received', 'closed', 'converted', 'confirmed', 'fulfilled', 'accepted', 'credit', 'admin'].includes(value)) {
      return 'badge--success';
    }
    if (['pending', 'draft', 'submitted', 'partially_paid', 'partially paid', 'partial', 'open', 'sent'].includes(value)) {
      return 'badge--warning';
    }
    if (['overdue', 'rejected', 'cancelled', 'failed', 'inactive', 'debit'].includes(value)) {
      return 'badge--danger';
    }
    return 'badge--neutral';
  }
}
