import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { FinanceApiService } from '../services/finance-api.service';

@Component({
  selector: 'app-reconciliation-page',
  standalone: true,
  imports: [
    FormsModule,
    PageHeaderComponent,
    FinanceBannerComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './reconciliation.page.html',
})
export class ReconciliationPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly toast = inject(ToastService);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'edit'));
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal('');
  note = '';
  updatedAt: string | null = null;

  ngOnInit(): void {
    this.api.getReconciliationNote().subscribe({
      next: (row) => {
        this.note = row.note ?? '';
        this.updatedAt = row.updatedAt;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load reconciliation notes.');
      },
    });
  }

  save(): void {
    if (!this.canEdit()) {
      return;
    }
    this.saving.set(true);
    this.api.saveReconciliationNote(this.note).subscribe({
      next: (row) => {
        this.saving.set(false);
        this.note = row.note;
        this.updatedAt = row.updatedAt;
        this.toast.success('Note saved');
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
