import { Injectable, inject } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { environment } from '../../../../environments/environment';
import { ApiClientService, ApiError } from '../../../core/api/api-client.service';
import { AuthService } from '../../../core/auth/auth.service';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';
import { compareMoney } from '../../../core/utils/money.util';
import { O2cStore } from '../../o2c/services/o2c.store';
import { P2pStore } from '../../p2p/services/p2p.store';
import {
  Category,
  DocumentMeta,
  Expense,
  FinanceAccount,
  FinanceQuery,
  FinanceTransaction,
  IncomeRecord,
  Offering,
  PageResult,
  Product,
  Subcategory,
} from '../models/finance.model';
import { FinanceStore } from './finance.store';

@Injectable({ providedIn: 'root' })
export class FinanceApiService {
  private readonly api = inject(ApiClientService);
  private readonly store = inject(FinanceStore);
  private readonly o2c = inject(O2cStore);
  private readonly p2p = inject(P2pStore);
  private readonly auth = inject(AuthService);

  listProducts(query: FinanceQuery = {}): Observable<PageResult<Product>> {
    return this.list('/products', query, () =>
      this.store.page(this.store.load().products, query, (item) => `${item.name} ${item.model} ${item.vinNumber}`),
    );
  }
  getProduct(id: string): Observable<Product | null> {
    return this.one(`/products/${id}`, () => this.store.load().products.find((row) => row.id === id) ?? null);
  }
  saveProduct(payload: Omit<Product, 'id' | 'organizationId' | 'createdAt'> & { id?: string }): Observable<Product> {
    const existing = payload.id ? this.store.load().products.find((row) => row.id === payload.id) : undefined;
    const record: Product = {
      ...payload,
      id: payload.id ?? this.store.nextId('prd'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
    };
    return this.write('/products', record, !payload.id, () => this.store.upsertProduct(record));
  }

  listCategories(query: FinanceQuery = {}): Observable<PageResult<Category>> {
    return this.list('/categories', query, () =>
      this.store.page(this.store.load().categories, query, (item) => `${item.name} ${item.description}`),
    );
  }
  saveCategory(payload: Omit<Category, 'id' | 'organizationId' | 'createdAt'> & { id?: string }): Observable<Category> {
    const existing = payload.id ? this.store.load().categories.find((row) => row.id === payload.id) : undefined;
    const record: Category = {
      ...payload,
      id: payload.id ?? this.store.nextId('cat'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
    };
    return this.write('/categories', record, !payload.id, () => this.store.upsertCategory(record));
  }

  listSubcategories(query: FinanceQuery = {}): Observable<PageResult<Subcategory>> {
    return this.list('/subcategories', query, () => {
      const items = query.categoryId
        ? this.store.load().subcategories.filter((row) => row.categoryId === query.categoryId)
        : this.store.load().subcategories;
      return this.store.page(items, { ...query, categoryId: undefined }, (item) => `${item.name} ${item.categoryName}`);
    });
  }
  saveSubcategory(
    payload: Omit<Subcategory, 'id' | 'organizationId' | 'createdAt' | 'categoryName'> & { id?: string },
  ): Observable<Subcategory> {
    const existing = payload.id ? this.store.load().subcategories.find((row) => row.id === payload.id) : undefined;
    const record: Subcategory = {
      ...payload,
      id: payload.id ?? this.store.nextId('sub'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      categoryName: '',
    };
    return this.write('/subcategories', record, !payload.id, () => this.store.upsertSubcategory(record));
  }

  listOfferings(query: FinanceQuery = {}): Observable<PageResult<Offering>> {
    return this.list('/offerings', query, () =>
      this.store.page(this.store.load().offerings, query, (item) => `${item.name} ${item.productName}`),
    );
  }
  saveOffering(
    payload: Omit<Offering, 'id' | 'organizationId' | 'createdAt' | 'productName'> & { id?: string },
  ): Observable<Offering> {
    const existing = payload.id ? this.store.load().offerings.find((row) => row.id === payload.id) : undefined;
    const record: Offering = {
      ...payload,
      id: payload.id ?? this.store.nextId('off'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      productName: '',
    };
    return this.write('/offerings', record, !payload.id, () => {
      const saved = this.store.upsertOffering(record);
      const o2c = this.o2c.load();
      const index = o2c.offerings.findIndex((row) => row.id === saved.id);
      const ref = { id: saved.id, name: saved.name };
      if (index >= 0) {
        o2c.offerings[index] = ref;
      } else {
        o2c.offerings.push(ref);
      }
      this.o2c.save(o2c);
      return saved;
    });
  }

  listExpenses(query: FinanceQuery = {}): Observable<PageResult<Expense>> {
    return this.api.getPaginated<Expense>('/finance/expenses', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getExpense(id: string): Observable<Expense | null> {
    return this.api.get<Expense>(`/finance/expenses/${id}`);
  }
  saveExpense(
    payload: Omit<
      Expense,
      | 'id'
      | 'organizationId'
      | 'createdAt'
      | 'vendorName'
      | 'categoryName'
      | 'subcategoryName'
      | 'productName'
      | 'enteredBy'
    > & { id?: string; enteredBy?: string },
  ): Observable<Expense> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating an expense is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<Expense>('/finance/expenses', {
      cost: payload.cost,
      expenseDate: payload.expenseDate,
      productServiceName: payload.productServiceName || null,
      vendorId: payload.vendorId || null,
    });
  }

  listIncome(query: FinanceQuery = {}): Observable<PageResult<IncomeRecord>> {
    return this.list('/income', query, () => this.store.page(this.buildIncome(), query, (item) => `${item.documentNumber} ${item.customerName}`));
  }

  listAccounts(query: FinanceQuery = {}): Observable<PageResult<FinanceAccount>> {
    return this.list('/finance/accounts', query, () =>
      this.store.page(this.store.load().accounts, query, (item) => `${item.name} ${item.accountNumber}`),
    );
  }
  getAccount(id: string): Observable<FinanceAccount | null> {
    return this.one(`/finance/accounts/${id}`, () => this.store.load().accounts.find((row) => row.id === id) ?? null);
  }
  saveAccount(
    payload: Omit<FinanceAccount, 'id' | 'organizationId' | 'createdAt'> & { id?: string },
  ): Observable<FinanceAccount> {
    const existing = payload.id ? this.store.load().accounts.find((row) => row.id === payload.id) : undefined;
    const record: FinanceAccount = {
      ...payload,
      id: payload.id ?? this.store.nextId('acc'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      balance: existing ? existing.balance : payload.balance,
    };
    return this.write('/finance/accounts', record, !payload.id, () => this.store.upsertAccount(record));
  }

  listTransactions(query: FinanceQuery = {}): Observable<PageResult<FinanceTransaction>> {
    return this.list('/finance/transactions', query, () =>
      this.store.page(this.store.load().transactions, query, (item) => `${item.accountName} ${item.description}`),
    );
  }
  getTransaction(id: string): Observable<FinanceTransaction | null> {
    return this.one(`/finance/transactions/${id}`, () => this.store.load().transactions.find((row) => row.id === id) ?? null);
  }
  saveTransaction(
    payload: Omit<FinanceTransaction, 'id' | 'organizationId' | 'createdAt' | 'accountName'> & { id?: string },
  ): Observable<FinanceTransaction> {
    if (compareMoney(payload.amount, '0.00') <= 0) {
      return throwError(() => ({ code: '400', message: 'Amount must be greater than zero.' } satisfies ApiError));
    }
    const existing = payload.id ? this.store.load().transactions.find((row) => row.id === payload.id) : undefined;
    const record: FinanceTransaction = {
      ...payload,
      id: payload.id ?? this.store.nextId('txn'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      accountName: '',
    };
    return this.write('/finance/transactions', record, !payload.id, () => this.store.upsertTransaction(record));
  }
  setReconciled(id: string, reconciled: boolean): Observable<FinanceTransaction> {
    return this.write(`/finance/transactions/${id}/reconcile`, { id, reconciled } as FinanceTransaction, false, () =>
      this.store.setReconciled(id, reconciled),
    );
  }

  listDocuments(query: FinanceQuery = {}): Observable<PageResult<DocumentMeta>> {
    return this.list('/documents', query, () =>
      this.store.page(this.store.load().documents, query, (item) => `${item.fileName} ${item.entityName} ${item.entityId}`),
    );
  }
  saveDocument(
    payload: Omit<DocumentMeta, 'id' | 'organizationId' | 'createdAt' | 'uploadedBy'> & { id?: string; uploadedBy?: string },
  ): Observable<DocumentMeta> {
    const existing = payload.id ? this.store.load().documents.find((row) => row.id === payload.id) : undefined;
    const record: DocumentMeta = {
      ...payload,
      id: payload.id ?? this.store.nextId('doc'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      uploadedBy: payload.uploadedBy ?? this.auth.session()?.fullName ?? 'User',
    };
    return this.write('/documents', record, !payload.id, () => this.store.upsertDocument(record));
  }

  private buildIncome(): IncomeRecord[] {
    const o2c = this.o2c.load();
    const invoices: IncomeRecord[] = o2c.invoices.map((row) => ({
      id: `inv-${row.id}`,
      sourceType: 'invoice',
      sourceId: row.id,
      sourceRoute: `/finance/invoices/${row.id}`,
      customerName: row.customerName,
      documentNumber: row.invoiceNumber,
      amount: row.invoiceAmount,
      gstAmount: row.isGstInvoice ? row.gstAmount : '0.00',
      date: row.invoiceRaisedDate,
      status: row.status,
    }));
    const receipts: IncomeRecord[] = o2c.receipts.map((row) => ({
      id: `rcp-${row.id}`,
      sourceType: 'receipt',
      sourceId: row.id,
      sourceRoute: `/finance/receipts/${row.id}`,
      customerName: o2c.invoices.find((invoice) => invoice.id === row.invoiceId)?.customerName ?? '',
      documentNumber: row.invoiceNumber,
      amount: row.receiptAmount,
      gstAmount: '0.00',
      date: row.receiptDate,
      status: row.paymentMode,
    }));
    const sales: IncomeRecord[] = o2c.salesInvoices.map((row) => ({
      id: `sinv-${row.id}`,
      sourceType: 'sales_invoice',
      sourceId: row.id,
      sourceRoute: `/o2c/sales-invoices/${row.id}`,
      customerName: row.customerName,
      documentNumber: row.invoiceNumber,
      amount: row.amount,
      gstAmount: row.gstAmount,
      date: row.invoiceDate,
      status: row.status,
    }));
    const collections: IncomeRecord[] = o2c.collections.map((row) => ({
      id: `col-${row.id}`,
      sourceType: 'collection',
      sourceId: row.id,
      sourceRoute: `/o2c/collections/${row.id}`,
      customerName: row.customerName,
      documentNumber: row.invoiceNumber,
      amount: row.amount,
      gstAmount: '0.00',
      date: row.collectionDate,
      status: row.status,
    }));
    return [...invoices, ...sales, ...receipts, ...collections].sort((a, b) => (a.date < b.date ? 1 : -1));
  }

  private orgId(): string {
    return this.auth.session()?.organizationId ?? DEMO_ORGANIZATION_ID;
  }

  private list<T>(path: string, query: FinanceQuery, fallback: () => PageResult<T>): Observable<PageResult<T>> {
    return this.api
      .get<T[]>(path, {
        page: query.page,
        pageSize: query.pageSize,
        search: query.search,
        status: query.status,
        vendorId: query.vendorId,
        categoryId: query.categoryId,
        accountId: query.accountId,
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
