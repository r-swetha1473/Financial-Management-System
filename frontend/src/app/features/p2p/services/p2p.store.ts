import { Injectable, inject } from '@angular/core';

import { AuditStore } from '../../../core/audit/audit.store';
import { AuthService } from '../../../core/auth/auth.service';
import { addMoney, compareMoney, subtractMoney } from '../../../core/utils/money.util';
import {
  GoodsReceipt,
  P2pQuery,
  P2pState,
  PageResult,
  Payable,
  PurchaseOrder,
  PurchaseRequest,
  SupplierInvoice,
  SupplierPayment,
  Vendor,
} from '../models/p2p.model';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';
import { createInitialP2pState } from '../seed/p2p.seed';

const PAGE_SIZE = 10;

@Injectable({ providedIn: 'root' })
export class P2pStore {
  private readonly auth = inject(AuthService);
  private readonly audit = inject(AuditStore);

  private key(): string {
    const orgId = this.auth.session()?.organizationId ?? DEMO_ORGANIZATION_ID;
    return `bfms_p2p_${orgId}`;
  }

  load(): P2pState {
    const raw = localStorage.getItem(this.key());
    if (!raw) {
      const initial = createInitialP2pState();
      this.save(initial);
      return initial;
    }
    try {
      return JSON.parse(raw) as P2pState;
    } catch {
      const initial = createInitialP2pState();
      this.save(initial);
      return initial;
    }
  }

  save(state: P2pState): void {
    localStorage.setItem(this.key(), JSON.stringify(state));
  }

  page<T extends { vendorId?: string | null; vendorName?: string; status?: string }>(
    items: T[],
    query: P2pQuery,
    searchFields: (item: T) => string,
  ): PageResult<T> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? PAGE_SIZE;
    const search = (query.search ?? '').trim().toLowerCase();
    const filtered = items.filter((item) => {
      const matchesSearch = !search || searchFields(item).toLowerCase().includes(search);
      const matchesStatus = !query.status || item.status === query.status;
      const matchesVendor = !query.vendorId || item.vendorId === query.vendorId;
      return matchesSearch && matchesStatus && matchesVendor;
    });
    const start = (page - 1) * pageSize;
    return {
      items: filtered.slice(start, start + pageSize),
      total: filtered.length,
      page,
      pageSize,
    };
  }

  nextId(prefix: string): string {
    return `${prefix}-${Date.now().toString(36)}`;
  }

  vendorName(state: P2pState, vendorId: string | null): string {
    if (!vendorId) {
      return '';
    }
    return state.vendors.find((vendor) => vendor.id === vendorId)?.name ?? '';
  }

  paidOnInvoice(state: P2pState, invoiceId: string): string {
    return state.payments
      .filter((payment) => payment.supplierInvoiceId === invoiceId && payment.status === 'completed')
      .reduce((sum, payment) => addMoney(sum, payment.amount), '0.00');
  }

  outstandingOnInvoice(state: P2pState, invoice: SupplierInvoice): string {
    return subtractMoney(invoice.amount, this.paidOnInvoice(state, invoice.id));
  }

  refreshInvoiceAndPayable(state: P2pState, invoiceId: string): void {
    const invoice = state.supplierInvoices.find((row) => row.id === invoiceId);
    if (!invoice || invoice.status === 'cancelled') {
      return;
    }
    const outstanding = this.outstandingOnInvoice(state, invoice);
    if (compareMoney(outstanding, '0.00') <= 0) {
      invoice.status = 'paid';
    } else if (compareMoney(this.paidOnInvoice(state, invoiceId), '0.00') > 0) {
      invoice.status = 'partially_paid';
    } else {
      invoice.status = 'pending';
    }

    const payable = state.payables.find((row) => row.sourceId === invoiceId);
    if (payable) {
      payable.outstanding = compareMoney(outstanding, '0.00') < 0 ? '0.00' : outstanding;
      if (compareMoney(payable.outstanding, '0.00') <= 0) {
        payable.status = 'closed';
      } else if (compareMoney(payable.outstanding, payable.amount) < 0) {
        payable.status = 'partial';
      } else {
        payable.status = 'open';
      }
    }
  }

  upsertVendor(vendor: Vendor): Vendor {
    const state = this.load();
    const existed = state.vendors.some((row) => row.id === vendor.id);
    const index = state.vendors.findIndex((row) => row.id === vendor.id);
    if (index >= 0) {
      state.vendors[index] = vendor;
    } else {
      state.vendors.unshift(vendor);
    }
    this.save(state);
    this.audit.record('vendor', vendor.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} vendor ${vendor.name}`);
    return vendor;
  }

  upsertPurchaseRequest(record: PurchaseRequest): PurchaseRequest {
    const state = this.load();
    const existed = state.purchaseRequests.some((row) => row.id === record.id);
    this.write(state.purchaseRequests, record);
    this.save(state);
    this.audit.record('purchase_request', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.requestNumber}`);
    return record;
  }

  upsertPurchaseOrder(record: PurchaseOrder): PurchaseOrder {
    const state = this.load();
    const existed = state.purchaseOrders.some((row) => row.id === record.id);
    this.write(state.purchaseOrders, record);
    if (record.purchaseRequestId) {
      const request = state.purchaseRequests.find((row) => row.id === record.purchaseRequestId);
      if (request && request.status !== 'rejected') {
        request.status = 'converted';
      }
    }
    this.save(state);
    this.audit.record('purchase_order', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.poNumber}`);
    return record;
  }

  upsertGoodsReceipt(record: GoodsReceipt): GoodsReceipt {
    const state = this.load();
    const existed = state.goodsReceipts.some((row) => row.id === record.id);
    this.write(state.goodsReceipts, record);
    const order = state.purchaseOrders.find((row) => row.id === record.purchaseOrderId);
    if (order && record.status === 'received') {
      order.status = 'received';
    }
    this.save(state);
    this.audit.record('goods_receipt', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.grnNumber}`);
    return record;
  }

  upsertSupplierInvoice(record: SupplierInvoice): SupplierInvoice {
    const state = this.load();
    const existed = state.supplierInvoices.some((row) => row.id === record.id);
    this.write(state.supplierInvoices, record);
    const existingPayable = state.payables.find((row) => row.sourceId === record.id);
    if (!existingPayable) {
      state.payables.unshift({
        id: this.nextId('ap'),
        organizationId: record.organizationId,
        sourceType: 'supplier_invoice',
        sourceId: record.id,
        invoiceNumber: record.invoiceNumber,
        vendorId: record.vendorId,
        vendorName: record.vendorName,
        amount: record.amount,
        outstanding: record.amount,
        dueDate: record.invoiceDate,
        status: 'open',
        createdAt: record.createdAt,
      });
    }
    this.refreshInvoiceAndPayable(state, record.id);
    this.save(state);
    this.audit.record('supplier_invoice', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.invoiceNumber}`);
    return record;
  }

  addPayment(record: SupplierPayment): SupplierPayment {
    const state = this.load();
    const invoice = state.supplierInvoices.find((row) => row.id === record.supplierInvoiceId);
    if (!invoice) {
      throw new Error('Supplier invoice not found.');
    }
    const outstanding = this.outstandingOnInvoice(state, invoice);
    if (compareMoney(record.amount, outstanding) > 0) {
      throw new Error('Payment cannot exceed the outstanding invoice amount.');
    }
    state.payments.unshift(record);
    this.refreshInvoiceAndPayable(state, invoice.id);
    this.save(state);
    this.audit.record('p2p_payment', record.id, 'create', `Recorded payment ${record.amount} for ${record.invoiceNumber}`);
    return record;
  }

  private write<T extends { id: string }>(items: T[], record: T): void {
    const index = items.findIndex((row) => row.id === record.id);
    if (index >= 0) {
      items[index] = record;
    } else {
      items.unshift(record);
    }
  }
}
