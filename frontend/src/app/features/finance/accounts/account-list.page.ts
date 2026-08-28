import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { FinanceAccount } from '../models/finance.model';
import { FinanceApiService } from '../services/finance-api.service';

@Component({
  selector: 'app-account-list-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    FinanceBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './account-list.page.html',
})
export class AccountListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  readonly loading = signal(true);
  readonly error = signal('');
  items: FinanceAccount[] = [];
  search = '';
  page = 1;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listAccounts({ page: 1, pageSize: 20 }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load accounts.');
      },
      });
  }

  get visibleItems(): FinanceAccount[] {
    const query = this.search.trim().toLowerCase();
    if (!query) {
      return this.items;
    }
    return this.items.filter(
      (row) => row.name.toLowerCase().includes(query) || row.accountType.toLowerCase().includes(query),
    );
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.page = 1;
    this.load();
  }
}
