import { Injectable, inject } from '@angular/core';
import { Observable, map, throwError } from 'rxjs';

import { ApiClientService, ApiError } from '../../../core/api/api-client.service';
import { addMoney, subtractMoney } from '../../../core/utils/money.util';
import {
  GoodsReceipt,
  P2pQuery,
  PageResult,
  Payable,
  PurchaseOrder,
  PurchaseRequest,
  SupplierInvoice,
  SupplierPayment,
  Vendor,
} from '../models/p2p.model';

const LIST_SIZE = 20;

@Injectable({ providedIn: 'root' })
export class P2pApiService {
  private readonly api = inject(ApiClientService);

  listVendors(query: P2pQuery = {}): Observable<PageResult<Vendor>> {
    return this.page('/p2p/vendors', query);
  }

  getVendor(id: string): Observable<Vendor | null> {
    return this.api.get<Vendor>(`/p2p/vendors/${id}`);
  }

  saveVendor(
    payload: Omit<Vendor, 'id' | 'organizationId' | 'createdAt'> & { id?: string },
  ): Observable<Vendor> {
    if (payload.id) {
      return this.unsupportedUpdate('vendor');
    }
    return this.api.post<Vendor>('/p2p/vendors', {
      name: payload.name,
      address: payload.address || null,
      phone: payload.phone || null,
      email: payload.email || null,
      pocName: payload.pocName || null,
      pocEmail: payload.pocEmail || null,
      gstin: payload.gstin || null,
      state: payload.state || null,
      status: payload.status,
    });
  }

  listPurchaseRequests(query: P2pQuery = {}): Observable<PageResult<PurchaseRequest>> {
    return this.page('/p2p/purchase-requests', query);
  }

  getPurchaseRequest(id: string): Observable<PurchaseRequest | null> {
    return this.api.get<PurchaseRequest>(`/p2p/purchase-requests/${id}`);
  }

  savePurchaseRequest(
    payload: Omit<PurchaseRequest, 'id' | 'organizationId' | 'createdAt' | 'vendorName'> & { id?: string },
  ): Observable<PurchaseRequest> {
    if (payload.id) {
      return this.unsupportedUpdate('purchase request');
    }
    return this.api.post<PurchaseRequest>('/p2p/purchase-requests', {
      vendorId: payload.vendorId || null,
      requestedDate: payload.requestedDate,
      notes: payload.notes || null,
      status: payload.status,
    });
  }

  approvePurchaseRequest(id: string): Observable<PurchaseRequest> {
    return this.api.patch<PurchaseRequest>(`/p2p/purchase-requests/${id}/approve`);
  }

  rejectPurchaseRequest(id: string): Observable<PurchaseRequest> {
    return this.api.patch<PurchaseRequest>(`/p2p/purchase-requests/${id}/reject`);
  }

  listPurchaseOrders(query: P2pQuery = {}): Observable<PageResult<PurchaseOrder>> {
    return this.page('/p2p/purchase-orders', query);
  }

  getPurchaseOrder(id: string): Observable<PurchaseOrder | null> {
    return this.api.get<PurchaseOrder>(`/p2p/purchase-orders/${id}`);
  }

  savePurchaseOrder(
    payload: Omit<PurchaseOrder, 'id' | 'organizationId' | 'createdAt' | 'vendorName' | 'purchaseRequestNumber'> & {
      id?: string;
    },
  ): Observable<PurchaseOrder> {
    if (payload.id) {
      return this.unsupportedUpdate('purchase order');
    }
    return this.api.post<PurchaseOrder>('/p2p/purchase-orders', {
      purchaseRequestId: payload.purchaseRequestId || null,
      vendorId: payload.vendorId,
      orderDate: payload.orderDate,
      totalAmount: payload.totalAmount,
      status: payload.status,
    });
  }

  issuePurchaseOrder(id: string): Observable<PurchaseOrder> {
    return this.api.patch<PurchaseOrder>(`/p2p/purchase-orders/${id}/issue`);
  }

  listGoodsReceipts(query: P2pQuery = {}): Observable<PageResult<GoodsReceipt>> {
    return this.page('/p2p/goods-receipts', query);
  }

  getGoodsReceipt(id: string): Observable<GoodsReceipt | null> {
    return this.api.get<GoodsReceipt>(`/p2p/goods-receipts/${id}`);
  }

  saveGoodsReceipt(
    payload: Omit<GoodsReceipt, 'id' | 'organizationId' | 'createdAt' | 'poNumber' | 'vendorId' | 'vendorName'> & {
      id?: string;
    },
  ): Observable<GoodsReceipt> {
    if (payload.id) {
      return this.unsupportedUpdate('goods receipt');
    }
    if (!payload.purchaseOrderId) {
      return throwError(() => ({ code: '400', message: 'Purchase order is required.' }) satisfies ApiError);
    }
    return this.api.post<GoodsReceipt>('/p2p/goods-receipts', {
      purchaseOrderId: payload.purchaseOrderId,
      receiptDate: payload.receiptDate,
      status: payload.status,
    });
  }

  listSupplierInvoices(query: P2pQuery = {}): Observable<PageResult<SupplierInvoice>> {
    return this.page('/p2p/supplier-invoices', query);
  }

  getSupplierInvoice(id: string): Observable<SupplierInvoice | null> {
    return this.api.get<SupplierInvoice>(`/p2p/supplier-invoices/${id}`);
  }

  saveSupplierInvoice(payload: {
    id?: string;
    goodsReceiptId: string | null;
    vendorId?: string | null;
    invoiceDate: string;
    amount: string;
    gstAmount: string;
  }): Observable<SupplierInvoice> {
    if (payload.id) {
      return this.unsupportedUpdate('supplier invoice');
    }
    if (!payload.goodsReceiptId) {
      return throwError(
        () =>
          ({
            code: '400',
            message: 'A received goods receipt is required to record a supplier invoice.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<SupplierInvoice>('/p2p/supplier-invoices', {
      goodsReceiptId: payload.goodsReceiptId,
      vendorId: payload.vendorId || null,
      invoiceDate: payload.invoiceDate,
      amount: payload.amount,
      gstAmount: payload.gstAmount,
    });
  }

  approveSupplierInvoice(id: string): Observable<SupplierInvoice> {
    return this.api.patch<SupplierInvoice>(`/p2p/supplier-invoices/${id}/approve`);
  }

  rejectSupplierInvoice(id: string): Observable<SupplierInvoice> {
    return this.api.patch<SupplierInvoice>(`/p2p/supplier-invoices/${id}/reject`);
  }

  listPayments(query: P2pQuery = {}): Observable<PageResult<SupplierPayment>> {
    return this.page('/p2p/payments', query);
  }

  getPayment(id: string): Observable<SupplierPayment | null> {
    return this.api.get<SupplierPayment>(`/p2p/payments/${id}`);
  }

  createPayment(
    payload: Omit<SupplierPayment, 'id' | 'organizationId' | 'createdAt' | 'invoiceNumber' | 'vendorId' | 'vendorName'>,
  ): Observable<SupplierPayment> {
    return this.api.post<SupplierPayment>('/p2p/payments', {
      supplierInvoiceId: payload.supplierInvoiceId,
      paymentDate: payload.paymentDate,
      amount: payload.amount,
      paymentMode: payload.paymentMode,
    });
  }

  listPayables(query: P2pQuery = {}): Observable<PageResult<Payable>> {
    return this.page('/p2p/payables', query);
  }

  getPayable(id: string): Observable<Payable | null> {
    return this.listPayables({ pageSize: 100 }).pipe(
      map((result) => result.items.find((row) => row.id === id || row.sourceId === id) ?? null),
    );
  }

  invoiceOutstanding(
    invoice: Pick<SupplierInvoice, 'id' | 'amount'> | null,
    payments: SupplierPayment[],
  ): { invoiceAmount: string; paid: string; outstanding: string } | null {
    if (!invoice) {
      return null;
    }
    const paid = payments
      .filter((row) => row.supplierInvoiceId === invoice.id && row.status !== 'cancelled')
      .reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    return {
      invoiceAmount: invoice.amount,
      paid,
      outstanding: subtractMoney(invoice.amount, paid),
    };
  }

  private page<T>(path: string, query: P2pQuery): Observable<PageResult<T>> {
    return this.api.getPaginated<T>(path, {
      page: query.page ?? 1,
      page_size: query.pageSize ?? LIST_SIZE,
      search: query.search,
      status: query.status,
      vendor_id: query.vendorId,
    });
  }

  private findInList<T extends { id: string }>(
    list$: Observable<PageResult<T>>,
    id: string,
  ): Observable<T | null> {
    return list$.pipe(map((result) => result.items.find((row) => row.id === id) ?? null));
  }

  private unsupportedUpdate<T>(entity: string): Observable<T> {
    return throwError(
      () =>
        ({
          code: '501',
          message: `Updating a ${entity} is not supported by the API yet.`,
        }) satisfies ApiError,
    );
  }
}
