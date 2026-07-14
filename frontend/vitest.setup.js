// Vitest global setup: provide a localStorage shim used by the API client.
class LocalStorageMock {
  constructor() {
    this.store = {}
  }
  getItem(key) {
    return key in this.store ? this.store[key] : null
  }
  setItem(key, value) {
    this.store[key] = String(value)
  }
  removeItem(key) {
    delete this.store[key]
  }
  clear() {
    this.store = {}
  }
}

globalThis.localStorage = new LocalStorageMock()
