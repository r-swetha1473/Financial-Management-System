import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Customer, Receivable } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-receivable-list-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    O2cBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './receivable-list.page.html',
})
export class ReceivableListPage implements OnInit {
  private readonly api = inject(O2cApiService);
  readonly loading = signal(true);
  readonly error = signal('');
  items: Receivable[] = [];
  customers: Customer[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  customerId = '';

  ngOnInit(): void {
    this.api.listCustomers({ pageSize: 100 }).subscribe((result) => (this.customers = result.items));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listReceivables({ page: this.page, search: this.search, status: this.status, customerId: this.customerId })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load receivables.');
        },
      });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'customer',
        label: 'Customer',
        blankLabel: 'All customers',
        value: this.customerId,
        options: this.customers.map((customer) => ({ value: customer.id, label: customer.name })),
      },
      {
        key: 'status',
        label: 'Status',
        blankLabel: 'All statuses',
        value: this.status,
        options: [
          { value: 'open', label: 'Open' },
          { value: 'partial', label: 'Partial' },
          { value: 'closed', label: 'Closed' },
        ],
      },
    ];
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.customerId = state.values['customer'] ?? '';
    this.status = state.values['status'] ?? '';
    this.page = 1;
    this.load();
  }
}
