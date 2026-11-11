## 0.3.0 (2026-10-25)

### 🚀 Features

- ⚠️ Release 2 - @rn-forge/ng-tailwind, RFC 9457 problems, event streams and
  invalidation ([59da8d0](https://github.com/rn-forge/ngkit/commit/59da8d0))

### ⚠️ Breaking Changes

- Release 2 - @rn-forge/ng-tailwind, RFC 9457 problems, event streams and
  invalidation ([59da8d0](https://github.com/rn-forge/ngkit/commit/59da8d0))
  @rn-forge/ng/crud's ProblemDetails and problemOf are removed; use Problem
  and problemOf from @rn-forge/ng/core. problemToFormErrors and crudErrorKind
  take the HttpErrorResponse, not a bare body. A problem is recognized by the
  application/problem+json media type, not by body shape.

### ❤️ Thank You

- Claude Opus 5.5
- Rohit Narayanan @rohitnarayanan

## 0.2.0 (2026-10-14)

### 🩹 Fixes

- ⚠️ **release:** apply the version bump as given below 1.0.0
  ([76f8901](https://github.com/rn-forge/ngkit/commit/76f8901))

### ⚠️ Breaking Changes

- **release:** apply the version bump as given below 1.0.0
  ([76f8901](https://github.com/rn-forge/ngkit/commit/76f8901)) Release 1
  changes the public API.
    - @rn-forge/ng/http and /http/crud are removed (AbstractHTTPService,
      BackendService, HttpUtil, DownloadResponse, apiBasePath); use HttpClient.
    - AuthBackendService requires backend.baseUrl when used.
    - FormUtil validators run on pristine values; DATE_RANGE(start?, end?) is a
      group validator; the old DATE_RANGE(formGroup, …) form is removed.
    - ObjectUtil.diff compares scalars strictly and arrays and dates structurally.
    - CrudDataSource and its types moved from @rn-forge/ng-bootstrap/crud to
      @rn-forge/ng/crud and changed shape (AIP-158 lists; get, delete and
      Versioned added; count/next/previous/results, BulkDeleteResponse,
      UploadResponse and upload removed).
    - The ng-bootstrap/crud mode 'upload' is now 'import', and 'download' is
      removed (export is a direct GET).
    - The permission keys .upload/.download are now .import/.export.
    - The CRUD table renders one server page with token paging; there are no
      numbered pages.

### ❤️ Thank You

- Claude Opus 5.5
- Rohit Narayanan @rohitnarayanan
