import { Component, EventEmitter, Output, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { hasPermission } from '../../rbac/permissions';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './topbar.component.html',
})
export class TopbarComponent {
  private readonly auth = inject(AuthService);

  @Output() menuToggle = new EventEmitter<void>();
  @Output() collapseToggle = new EventEmitter<void>();

  readonly menuOpen = signal(false);
  readonly session = this.auth.session;
  readonly canAdmin = computed(() => hasPermission(this.session()?.role, 'admin'));

  initials(): string {
    const name = this.session()?.fullName ?? 'User';
    return name
      .split(' ')
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase();
  }

  logout(): void {
    this.menuOpen.set(false);
    this.auth.logout();
  }
}
