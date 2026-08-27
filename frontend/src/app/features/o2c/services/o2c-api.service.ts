import { Injectable, inject } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { environment } from '../../../../environments/environment';
import { ApiClientService, ApiError } from '../../../core/api/api-client.service';
import { AuthService } from '../../../core/auth/auth.service';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';
import { subtractMoney } from '../../../core/utils/money.util';
import {
  Booking,
  Collection,
  Customer,
  Delivery,
  InvoiceReceipt,
  LegacyInvoice,
  O2cQuery,
  OfferingRef,
  PageResult,
  PlanRef,
  Quotation,
  Receivable,
  SalesInvoice,
  SalesOrder,
} from '../models/o2c.model';
import { O2cStore } from './o2c.store';

@Injectable({ providedIn: 'root' })
export class O2cApiService {
  private readonly api = inject(ApiClientService);
  private readonly store = inject(O2cStore);
  private readonly auth = inject(AuthService);

  listCustomers(query: O2cQuery = {}): Observable<PageResult<Customer>> {
    return this.api.getPaginated<Customer>('/o2c/customers', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getCustomer(id: string): Observable<Customer | null> {
    return this.api.get<Customer>(`/o2c/customers/${id}`);
  }
  saveCustomer(
    payload: Omit<Customer, 'id' | 'organizationId' | 'createdAt'> & { id?: string },
  ): Observable<Customer> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a customer is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<Customer>('/o2c/customers', {
      name: payload.name,
      address: payload.address || null,
      gstin: payload.gstin || null,
      state: payload.state || null,
      creditLimit: payload.creditLimit || null,
    });
  }

  offerings(): OfferingRef[] {
    return this.store.load().offerings;
  }
  plans(): PlanRef[] {
    return this.store.load().plans;
  }

  listQuotations(query: O2cQuery = {}): Observable<PageResult<Quotation>> {
    return this.api.getPaginated<Quotation>('/o2c/quotations', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getQuotation(id: string): Observable<Quotation | null> {
    return this.api.get<Quotation>(`/o2c/quotations/${id}`);
  }
  saveQuotation(
    payload: Omit<Quotation, 'id' | 'organizationId' | 'createdAt' | 'customerName'> & { id?: string },
  ): Observable<Quotation> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a quotation is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<Quotation>('/o2c/quotations', {
      customerId: payload.customerId,
      quoteDate: payload.quoteDate,
      validUntil: payload.validUntil || null,
      totalAmount: payload.totalAmount,
      status: payload.status,
    });
  }

  listSalesOrders(query: O2cQuery = {}): Observable<PageResult<SalesOrder>> {
    return this.api.getPaginated<SalesOrder>('/o2c/sales-orders', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getSalesOrder(id: string): Observable<SalesOrder | null> {
    return this.api.get<SalesOrder>(`/o2c/sales-orders/${id}`);
  }
  saveSalesOrder(
    payload: Omit<SalesOrder, 'id' | 'organizationId' | 'createdAt' | 'customerName' | 'quoteNumber'> & { id?: string },
  ): Observable<SalesOrder> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a sales order is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<SalesOrder>('/o2c/sales-orders', {
      customerId: payload.customerId,
      quotationId: payload.quotationId || null,
      orderDate: payload.orderDate,
      totalAmount: payload.totalAmount,
      status: payload.status,
    });
  }

  listDeliveries(query: O2cQuery = {}): Observable<PageResult<Delivery>> {
    return this.api.getPaginated<Delivery>('/o2c/deliveries', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getDelivery(id: string): Observable<Delivery | null> {
    return this.api.get<Delivery>(`/o2c/deliveries/${id}`);
  }
  saveDelivery(
    payload: Omit<Delivery, 'id' | 'organizationId' | 'createdAt' | 'orderNumber' | 'customerId' | 'customerName'> & {
      id?: string;
    },
  ): Observable<Delivery> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a delivery is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<Delivery>('/o2c/deliveries', {
      salesOrderId: payload.salesOrderId,
      deliveryDate: payload.deliveryDate,
      status: payload.status,
    });
  }

  listSalesInvoices(query: O2cQuery = {}): Observable<PageResult<SalesInvoice>> {
    return this.api.getPaginated<SalesInvoice>('/o2c/sales-invoices', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getSalesInvoice(id: string): Observable<SalesInvoice | null> {
    return this.api.get<SalesInvoice>(`/o2c/sales-invoices/${id}`);
  }
  saveSalesInvoice(
    payload: Omit<
      SalesInvoice,
      'id' | 'organizationId' | 'createdAt' | 'customerName' | 'orderNumber' | 'deliveryNumber' | 'approvalStatus' | 'outstanding'
    > & { id?: string },
  ): Observable<SalesInvoice> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a sales invoice is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<SalesInvoice>('/o2c/sales-invoices', {
      deliveryId: payload.deliveryId,
      customerId: payload.customerId || null,
      salesOrderId: payload.salesOrderId || null,
      invoiceDate: payload.invoiceDate,
      amount: payload.amount,
      gstAmount: payload.gstAmount,
    });
  }
  approveSalesInvoice(id: string): Observable<SalesInvoice> {
    return this.api.patch<SalesInvoice>(`/o2c/sales-invoices/${id}/approve`);
  }
  rejectSalesInvoice(id: string): Observable<SalesInvoice> {
    return this.api.patch<SalesInvoice>(`/o2c/sales-invoices/${id}/reject`);
  }

  listCollections(query: O2cQuery = {}): Observable<PageResult<Collection>> {
    return this.api.getPaginated<Collection>('/o2c/collections', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getCollection(id: string): Observable<Collection | null> {
    return this.api.get<Collection>(`/o2c/collections/${id}`);
  }
  createCollection(
    payload: Omit<Collection, 'id' | 'organizationId' | 'createdAt' | 'invoiceNumber' | 'customerId' | 'customerName'>,
  ): Observable<Collection> {
    return this.api.post<Collection>('/o2c/collections', {
      salesInvoiceId: payload.salesInvoiceId,
      collectionDate: payload.collectionDate,
      amount: payload.amount,
      paymentMode: payload.paymentMode,
    });
  }

  listReceivables(query: O2cQuery = {}): Observable<PageResult<Receivable>> {
    return this.api.getPaginated<Receivable>('/o2c/receivables', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getReceivable(id: string): Observable<Receivable | null> {
    return this.api.get<Receivable>(`/o2c/receivables/${id}`);
  }

  salesInvoiceOutstanding(invoice: Pick<SalesInvoice, 'amount' | 'outstanding'> | null) {
    if (!invoice) {
      return null;
    }
    const outstanding = invoice.outstanding ?? invoice.amount;
    return { invoiceAmount: invoice.amount, paid: subtractMoney(invoice.amount, outstanding), outstanding };
  }

  listBookings(query: O2cQuery = {}): Observable<PageResult<Booking>> {
    return this.list('/bookings', query, () =>
      this.store.page(this.store.load().bookings, query, (item) => `${item.offeringName} ${item.customerName}`),
    );
  }
  getBooking(id: string): Observable<Booking | null> {
    return this.one(`/bookings/${id}`, () => this.store.load().bookings.find((row) => row.id === id) ?? null);
  }
  saveBooking(
    payload: Omit<Booking, 'id' | 'organizationId' | 'createdAt' | 'customerName' | 'offeringName'> & { id?: string },
  ): Observable<Booking> {
    const state = this.store.load();
    const existing = payload.id ? state.bookings.find((row) => row.id === payload.id) : undefined;
    const record: Booking = {
      ...payload,
      id: payload.id ?? this.store.nextId('bk'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      customerName: this.store.customerName(state, payload.customerId),
      offeringName: state.offerings.find((row) => row.id === payload.offeringId)?.name ?? '',
    };
    return this.write('/bookings', record, !payload.id, () => this.store.upsertBooking(record));
  }

  listInvoices(query: O2cQuery = {}): Observable<PageResult<LegacyInvoice>> {
    return this.list('/invoices', query, () =>
      this.store.page(this.store.load().invoices, query, (item) => `${item.invoiceNumber} ${item.customerName}`),
    );
  }
  getInvoice(id: string): Observable<LegacyInvoice | null> {
    return this.one(`/invoices/${id}`, () => this.store.load().invoices.find((row) => row.id === id) ?? null);
  }
  saveInvoice(
    payload: Omit<
      LegacyInvoice,
      'id' | 'organizationId' | 'createdAt' | 'customerName' | 'bookingLabel' | 'planName' | 'status'
    > & { id?: string },
  ): Observable<LegacyInvoice> {
    const state = this.store.load();
    const booking = state.bookings.find((row) => row.id === payload.bookingId);
    const plan = state.plans.find((row) => row.id === payload.planId);
    const existing = payload.id ? state.invoices.find((row) => row.id === payload.id) : undefined;
    const record: LegacyInvoice = {
      ...payload,
      id: payload.id ?? this.store.nextId('inv'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      customerName: this.store.customerName(state, payload.customerId),
      bookingLabel: booking?.offeringName ?? '',
      planName: plan?.name ?? '',
      status: existing?.status ?? 'pending',
    };
    return this.write('/invoices', record, !payload.id, () => this.store.upsertLegacyInvoice(record));
  }

  listReceipts(query: O2cQuery = {}): Observable<PageResult<InvoiceReceipt>> {
    return this.list('/receipts', query, () => {
      const state = this.store.load();
      const invoiceIds = query.customerId
        ? state.invoices.filter((row) => row.customerId === query.customerId).map((row) => row.id)
        : null;
      const items = invoiceIds ? state.receipts.filter((row) => invoiceIds.includes(row.invoiceId)) : state.receipts;
      return this.store.page(items, { ...query, customerId: undefined }, (item) => `${item.invoiceNumber} ${item.paymentMode}`);
    });
  }
  getReceipt(id: string): Observable<InvoiceReceipt | null> {
    return this.one(`/receipts/${id}`, () => this.store.load().receipts.find((row) => row.id === id) ?? null);
  }
  createReceipt(
    payload: Omit<InvoiceReceipt, 'id' | 'organizationId' | 'createdAt' | 'invoiceNumber' | 'pendingAmount' | 'enteredBy'> & {
      enteredBy?: string;
    },
  ): Observable<InvoiceReceipt> {
    const invoice = this.store.load().invoices.find((row) => row.id === payload.invoiceId);
    if (!invoice) {
      return throwError(() => ({ code: '400', message: 'Invoice is required.' } satisfies ApiError));
    }
    if (payload.paymentMode === 'UPI' && !/^\d{4}$/.test(payload.transactionLast4)) {
      return throwError(() => ({ code: '400', message: 'UPI receipts require exactly 4 digits.' } satisfies ApiError));
    }
    const record: InvoiceReceipt = {
      ...payload,
      id: this.store.nextId('rcp'),
      organizationId: this.orgId(),
      createdAt: today(),
      invoiceNumber: invoice.invoiceNumber,
      pendingAmount: '0.00',
      enteredBy: payload.enteredBy ?? this.auth.session()?.fullName ?? 'User',
    };
    return this.write('/receipts', record, true, () => this.store.addReceipt(record));
  }

  legacyInvoiceOutstanding(id: string) {
    const state = this.store.load();
    const invoice = state.invoices.find((row) => row.id === id);
    if (!invoice) {
      return null;
    }
    const paid = this.store.paidOnLegacyInvoice(state, id);
    return {
      invoiceAmount: invoice.invoiceAmount,
      paid,
      outstanding: subtractMoney(invoice.invoiceAmount, paid),
    };
  }

  private orgId(): string {
    return this.auth.session()?.organizationId ?? DEMO_ORGANIZATION_ID;
  }

  private list<T>(path: string, query: O2cQuery, fallback: () => PageResult<T>): Observable<PageResult<T>> {
    return this.api
      .get<T[]>(path, {
        page: query.page,
        pageSize: query.pageSize,
        search: query.search,
        status: query.status,
        customerId: query.customerId,
      })
      .pipe(
        map((data) => ({ items: data, total: data.length, page: query.page ?? 1, pageSize: query.pageSize ?? 10 })),
        catchError((error: ApiError) => (environment.useDevSeed ? of(fallback()) : throwError(() => error))),
      );
  }

  private one<T>(path: string, fallback: () => T): Observable<T> {
    return this.api.get<T>(path).pipe(
      catchError((error: ApiError) => (environment.useDevSeed ? of(fallback()) : throwError(() => error))),
    );
  }

  private write<T extends { id: string }>(path: string, body: T, isNew: boolean, fallback: () => T): Observable<T> {
    const request$ = isNew ? this.api.post<T>(path, body) : this.api.put<T>(`${path}/${body.id}`, body);
    return request$.pipe(
      catchError((error: ApiError) => {
        if (!environment.useDevSeed) {
          return throwError(() => error);
        }
        try {
          return of(fallback());
        } catch (storeError) {
          return throwError(() => ({
            code: '400',
            message: storeError instanceof Error ? storeError.message : error.message,
          } satisfies ApiError));
        }
      }),
    );
  }
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}
