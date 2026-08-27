import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { addMoney } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { FinanceAccount, FinanceTransaction } from '../models/finance.model';
import { FinanceApiService } from '../services/finance-api.service';

@Component({
  selector: 'app-reconciliation-page',
  standalone: true,
  imports: [
    FormsModule,
    PageHeaderComponent,
    FinanceBannerComponent,
    StatusBadgeComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './reconciliation.page.html',
})
export class ReconciliationPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly toast = inject(ToastService);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'edit'));
  readonly loading = signal(true);
  accounts: FinanceAccount[] = [];
  items: FinanceTransaction[] = [];
  accountId = '';

  ngOnInit(): void {
    this.api.listAccounts({ pageSize: 100 }).subscribe((result) => {
      this.accounts = result.items;
      this.accountId = this.accounts[0]?.id ?? '';
      this.load();
    });
  }

  load(): void {
    this.loading.set(true);
    this.api.listTransactions({ pageSize: 100, accountId: this.accountId }).subscribe((result) => {
      this.items = result.items;
      this.loading.set(false);
    });
  }

  selected(): FinanceAccount | undefined {
    return this.accounts.find((row) => row.id === this.accountId);
  }

  unmatchedTotal(): string {
    return this.items.filter((row) => !row.reconciled).reduce((sum, row) => addMoney(sum, row.amount), '0.00');
  }

  toggle(row: FinanceTransaction): void {
    if (!this.canEdit()) {
      return;
    }
    this.api.setReconciled(row.id, !row.reconciled).subscribe({
      next: () => {
        this.toast.success(row.reconciled ? 'Marked unreconciled' : 'Marked reconciled');
        this.load();
      },
      error: (err) => this.toast.error('Update failed', err.message),
    });
  }
}
