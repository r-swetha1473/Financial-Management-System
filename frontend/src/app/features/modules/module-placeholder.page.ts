import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';

import { O2C_WORKFLOW_STEPS, P2P_WORKFLOW_STEPS } from '../../core/navigation/nav.config';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';

export interface ModulePageData {
  title: string;
  subtitle: string;
  module: 'p2p' | 'o2c' | 'finance' | 'master' | 'reports' | 'admin';
  phase: number;
  workflow?: 'p2p' | 'o2c';
  currentStep?: string;
}

@Component({
  selector: 'app-module-placeholder-page',
  standalone: true,
  imports: [PageHeaderComponent, EmptyStateComponent],
  templateUrl: './module-placeholder.page.html',
})
export class ModulePlaceholderPage {
  private readonly route = inject(ActivatedRoute);
  readonly data = toSignal(this.route.data, { initialValue: this.route.snapshot.data });
  readonly page = computed(() => this.data() as ModulePageData);
  readonly steps = computed(() => (this.page().workflow === 'o2c' ? O2C_WORKFLOW_STEPS : P2P_WORKFLOW_STEPS));
  readonly bannerClass = computed(() => (this.page().workflow === 'o2c' ? 'workflow-banner--o2c' : 'workflow-banner--p2p'));
}
