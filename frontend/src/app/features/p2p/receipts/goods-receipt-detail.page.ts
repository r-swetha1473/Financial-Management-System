import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { GoodsReceipt, SupplierInvoice } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-goods-receipt-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, P2pBannerComponent, StatusBadgeComponent, DocumentTrailComponent, EmptyStateComponent],
  templateUrl: './goods-receipt-detail.page.html',
})
export class GoodsReceiptDetailPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  record: GoodsReceipt | null = null;
  invoices: SupplierInvoice[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({
      record: this.api.getGoodsReceipt(id),
      invoices: this.api.listSupplierInvoices({ pageSize: 50 }),
    }).subscribe({
      next: (data) => {
        this.record = data.record;
        this.invoices = data.invoices.items.filter((row) => row.goodsReceiptId === id);
      },
      error: () => {
        this.record = null;
      },
    });
  }
}
