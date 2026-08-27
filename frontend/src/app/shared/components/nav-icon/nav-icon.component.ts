import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-nav-icon',
  standalone: true,
  template: `
    <svg class="sidebar__link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
      @switch (name) {
        @case ('dashboard') {
          <rect x="3" y="3" width="8" height="8" rx="1.5" />
          <rect x="13" y="3" width="8" height="5" rx="1.5" />
          <rect x="13" y="10" width="8" height="11" rx="1.5" />
          <rect x="3" y="13" width="8" height="8" rx="1.5" />
        }
        @case ('request') {
          <path d="M8 7h8M8 12h5M7 4h10a2 2 0 0 1 2 2v14l-4-2-4 2-4-2-4 2V6a2 2 0 0 1 2-2Z" />
        }
        @case ('order') {
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <path d="M8 9h8M8 13h5" />
        }
        @case ('receipt') {
          <path d="M7 4h10v16l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5-2 1.5V4Z" />
        }
        @case ('invoice') {
          <path d="M7 3h8l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
          <path d="M15 3v5h5" />
        }
        @case ('payment') {
          <rect x="3" y="6" width="18" height="12" rx="2" />
          <path d="M3 10h18" />
        }
        @case ('payable') {
          <circle cx="12" cy="12" r="8" />
          <path d="M12 8v8M9 15h6" />
        }
        @case ('quote') {
          <path d="M8 8h8v5H9l-1 3V8Z" />
          <path d="M6 5h12" />
        }
        @case ('delivery') {
          <path d="M3 7h11v10H3zM14 11h5l2 3v3h-7" />
          <circle cx="7" cy="18" r="1.5" />
          <circle cx="17" cy="18" r="1.5" />
        }
        @case ('collection') {
          <path d="M12 4v16M8 8h8M8 16h8" />
        }
        @case ('receivable') {
          <circle cx="12" cy="12" r="8" />
          <path d="M12 8v8M15 9H10a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H9" />
        }
        @case ('expense') {
          <path d="M12 5v14M8 9l4-4 4 4" />
        }
        @case ('income') {
          <path d="M12 19V5M8 15l4 4 4-4" />
        }
        @case ('transaction') {
          <path d="M4 7h12l-3-3M20 17H8l3 3" />
        }
        @case ('account') {
          <rect x="3" y="6" width="18" height="12" rx="2" />
          <circle cx="16" cy="12" r="1.5" />
        }
        @case ('tax') {
          <path d="M4 20 20 4M7 7h.01M17 17h.01" />
        }
        @case ('reconcile') {
          <path d="M4 12a8 8 0 0 1 14-4M20 12a8 8 0 0 1-14 4" />
        }
        @case ('booking') {
          <rect x="4" y="5" width="16" height="15" rx="2" />
          <path d="M8 3v4M16 3v4M4 10h16" />
        }
        @case ('vendor') {
          <path d="M4 20v-8l8-5 8 5v8H4Z" />
        }
        @case ('customer') {
          <circle cx="12" cy="8" r="3" />
          <path d="M5 20c1.5-4 4-6 7-6s5.5 2 7 6" />
        }
        @case ('product') {
          <path d="M4 8l8-4 8 4-8 4-8-4Zm0 0v8l8 4 8-4V8" />
        }
        @case ('category') {
          <rect x="4" y="4" width="7" height="7" rx="1" />
          <rect x="13" y="4" width="7" height="7" rx="1" />
          <rect x="4" y="13" width="7" height="7" rx="1" />
          <rect x="13" y="13" width="7" height="7" rx="1" />
        }
        @case ('service') {
          <circle cx="12" cy="12" r="3" />
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
        }
        @case ('report') {
          <path d="M5 19V9l5-2 4 2 5-2v12l-5 2-4-2-5 2Z" />
        }
        @case ('users') {
          <circle cx="9" cy="8" r="3" />
          <path d="M3 20c.8-4 3-6 6-6s5.2 2 6 6M17 11a3 3 0 1 0 0-6" />
        }
        @case ('reference') {
          <path d="M6 4h12v16H6zM9 8h6M9 12h6" />
        }
        @case ('audit') {
          <circle cx="11" cy="11" r="6" />
          <path d="m20 20-4-4" />
        }
        @case ('document') {
          <path d="M7 3h8l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
        }
        @case ('settings') {
          <circle cx="12" cy="12" r="3" />
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3 5.6 18.4" />
        }
        @default {
          <circle cx="12" cy="12" r="7" />
        }
      }
    </svg>
  `,
})
export class NavIconComponent {
  @Input({ required: true }) name = 'dashboard';
}
