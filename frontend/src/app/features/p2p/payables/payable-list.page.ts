import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { Payable, Vendor } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-payable-list-page',
  standalone: true,
  imports: [
    FormsModule,
    RouterLink,
    PageHeaderComponent,
    P2pBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './payable-list.page.html',
})
export class PayableListPage implements OnInit {
  private readonly api = inject(P2pApiService);
  readonly loading = signal(true);
  readonly error = signal('');
  items: Payable[] = [];
  vendors: Vendor[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  vendorId = '';

  ngOnInit(): void {
    this.api.listVendors({ pageSize: 100 }).subscribe((result) => (this.vendors = result.items));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listPayables({ page: this.page, search: this.search, status: this.status, vendorId: this.vendorId }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load payables.');
      },
    });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'vendor',
        label: 'Vendor',
        blankLabel: 'All Vendors',
        value: this.vendorId,
        options: this.vendors.map((vendor) => ({ value: vendor.id, label: vendor.name })),
      },
      {
        key: 'status',
        label: 'Status',
        blankLabel: 'All Statuses',
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
    this.vendorId = state.values['vendor'] ?? '';
    this.status = state.values['status'] ?? '';
    this.page = 1;
    this.load();
  }
}
