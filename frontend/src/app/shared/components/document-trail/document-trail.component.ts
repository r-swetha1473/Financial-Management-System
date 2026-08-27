import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { StatusBadgeComponent } from '../status-badge/status-badge.component';

export interface DocumentTrailItem {
  label: string;
  value: string;
  route?: string | null;
  status?: string;
}

@Component({
  selector: 'app-document-trail',
  standalone: true,
  imports: [RouterLink, StatusBadgeComponent],
  template: `
    <div class="doc-trail" aria-label="Related documents">
      @for (item of items; track item.label) {
        @if (item.route) {
          <a class="doc-trail__item is-link" [routerLink]="item.route">
            <span class="doc-trail__label">{{ item.label }}</span>
            <span class="doc-trail__value">{{ item.value }}</span>
            @if (item.status) {
              <app-status-badge [status]="item.status" />
            }
          </a>
        } @else {
          <div class="doc-trail__item">
            <span class="doc-trail__label">{{ item.label }}</span>
            <span class="doc-trail__value">{{ item.value }}</span>
            @if (item.status) {
              <app-status-badge [status]="item.status" />
            }
          </div>
        }
      }
    </div>
  `,
})
export class DocumentTrailComponent {
  @Input({ required: true }) items: DocumentTrailItem[] = [];
}
