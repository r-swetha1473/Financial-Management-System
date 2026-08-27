import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  template: `
    <div class="empty-state">
      <div class="empty-state__icon">{{ icon }}</div>
      <h3>{{ title }}</h3>
      <p>{{ message }}</p>
      <ng-content />
    </div>
  `,
})
export class EmptyStateComponent {
  @Input() icon = '◇';
  @Input() title = 'Nothing to show yet';
  @Input() message = 'Records will appear here once they are created.';
}
