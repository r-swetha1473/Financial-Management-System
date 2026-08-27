import { Component, Input, Output, EventEmitter, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { NavSection, visibleNavSections } from '../../navigation/nav.config';
import { NavIconComponent } from '../../../shared/components/nav-icon/nav-icon.component';
import { BrandMarkComponent } from '../../../shared/components/brand-mark/brand-mark.component';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, NavIconComponent, BrandMarkComponent],
  templateUrl: './sidebar.component.html',
  host: { style: 'display: contents' },
})
export class SidebarComponent {
  private readonly auth = inject(AuthService);

  @Input() collapsed = false;
  @Input() mobileOpen = false;
  @Output() navigate = new EventEmitter<void>();

  readonly sections = computed(() => visibleNavSections(this.auth.session()?.role));

  overviewRoute(module?: NavSection['module']): string | null {
    if (module === 'p2p') {
      return '/p2p';
    }
    if (module === 'o2c') {
      return '/o2c';
    }
    return null;
  }

  onNavigate(): void {
    this.navigate.emit();
  }
}
