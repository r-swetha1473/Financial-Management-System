import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
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
}
