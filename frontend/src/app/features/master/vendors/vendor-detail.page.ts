import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { P2pBannerComponent } from '../../p2p/components/p2p-banner.component';
import {
  GoodsReceipt,
  PurchaseOrder,
  PurchaseRequest,
  SupplierInvoice,
  Vendor,
} from '../../p2p/models/p2p.model';
import { P2pApiService } from '../../p2p/services/p2p-api.service';

@Component({
  selector: 'app-vendor-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    P2pBannerComponent,
    StatusBadgeComponent,
    DocumentTrailComponent,
    EmptyStateComponent,
  ],
  templateUrl: './vendor-detail.page.html',
})
export class VendorDetailPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  vendor: Vendor | null = null;
  requests: PurchaseRequest[] = [];
  orders: PurchaseOrder[] = [];
  receipts: GoodsReceipt[] = [];
  invoices: SupplierInvoice[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({
      vendor: this.api.getVendor(id),
      requests: this.api.listPurchaseRequests({ vendorId: id, pageSize: 20 }),
      orders: this.api.listPurchaseOrders({ vendorId: id, pageSize: 20 }),
      receipts: this.api.listGoodsReceipts({ vendorId: id, pageSize: 20 }),
      invoices: this.api.listSupplierInvoices({ vendorId: id, pageSize: 20 }),
    }).subscribe({
      next: (data) => {
        this.vendor = data.vendor;
        this.requests = data.requests.items;
        this.orders = data.orders.items;
        this.receipts = data.receipts.items;
        this.invoices = data.invoices.items;
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
