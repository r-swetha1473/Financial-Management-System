import { Component, HostListener, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { SidebarComponent } from '../sidebar/sidebar.component';
import { TopbarComponent } from '../topbar/topbar.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, SidebarComponent, TopbarComponent],
  templateUrl: './app-shell.component.html',
})
export class AppShellComponent {
  readonly collapsed = signal(false);
  readonly mobileOpen = signal(false);

  toggleCollapsed(): void {
    if (window.innerWidth < 1024) {
      this.mobileOpen.update((open) => !open);
      return;
    }
    this.collapsed.update((value) => !value);
  }

  closeMobile(): void {
    this.mobileOpen.set(false);
  }

  @HostListener('window:resize')
  onResize(): void {
    if (window.innerWidth >= 1024) {
      this.mobileOpen.set(false);
    }
  }
}
