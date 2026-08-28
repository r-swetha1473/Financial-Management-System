import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { FinanceAccount, FinanceTransaction } from '../models/finance.model';
import { FinanceApiService } from '../services/finance-api.service';

@Component({
  selector: 'app-transaction-list-page',
  standalone: true,
  imports: [
    PageHeaderComponent,
    FinanceBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './transaction-list.page.html',
})
export class TransactionListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly route = inject(ActivatedRoute);
  readonly loading = signal(true);
  readonly error = signal('');
  items: FinanceTransaction[] = [];
  accounts: FinanceAccount[] = [];
  total = 0;
  page = 1;
  search = '';
  accountId = '';

  ngOnInit(): void {
    this.accountId = this.route.snapshot.queryParamMap.get('accountId') ?? '';
    this.api.listAccounts({ pageSize: 20 }).subscribe((result) => (this.accounts = result.items));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listTransactions({ page: this.page, search: this.search, accountId: this.accountId }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load transactions.');
      },
      });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'account',
        label: 'Account',
        blankLabel: 'All accounts',
        value: this.accountId,
        options: this.accounts.map((account) => ({ value: account.id, label: account.name })),
      },
    ];
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.accountId = state.values['account'] ?? '';
    this.page = 1;
    this.load();
  }
}
