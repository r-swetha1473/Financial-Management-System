import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { GoodsReceipt, PurchaseOrder } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-purchase-order-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    P2pBannerComponent,
    StatusBadgeComponent,
    DocumentTrailComponent,
    EmptyStateComponent,
    InrPipe,
  ],
  templateUrl: './purchase-order-detail.page.html',
})
export class PurchaseOrderDetailPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  record: PurchaseOrder | null = null;
  receipts: GoodsReceipt[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({
      record: this.api.getPurchaseOrder(id),
      receipts: this.api.listGoodsReceipts({ pageSize: 50 }),
    }).subscribe({
      next: (data) => {
        this.record = data.record;
        this.receipts = data.receipts.items.filter((row) => row.purchaseOrderId === id);
      },
      error: () => {
        this.record = null;
      },
    });
  }
}
