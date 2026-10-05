const DATABASE = "drosophila-local-reading-v1";
const TABLE = "reading";

function openDatabase(factory) {
  if (!factory)
    return Promise.reject(new Error("Local storage is unavailable."));
  return new Promise((resolve, reject) => {
    const request = factory.open(DATABASE, 1);
    let settled = false;
    const fail = (error) => {
      settled = true;
      clearTimeout(timer);
      reject(error);
    };
    const timer = setTimeout(
      () => fail(new Error("Local storage did not respond.")),
      5000,
    );
    request.onupgradeneeded = () => request.result.createObjectStore(TABLE);
    request.onerror = () => fail(request.error);
    request.onblocked = () =>
      fail(new Error("Another tab is blocking local storage."));
    request.onsuccess = () => {
      clearTimeout(timer);
      if (settled) {
        request.result.close();
        return;
      }
      const db = request.result;
      db.onversionchange = () => db.close();
      resolve(db);
    };
  });
}

// One completed reading, explicitly reopenable/deletable; never sent to a server.
export class ResultStore {
  constructor(factory = globalThis.indexedDB) {
    this.factory = factory;
  }
  async transact(mode, action, signal) {
    const db = await openDatabase(this.factory);
    try {
      signal?.throwIfAborted();
      return await new Promise((resolve, reject) => {
        const tx = db.transaction(TABLE, mode),
          store = tx.objectStore(TABLE);
        let result;
        const abort = () => {
          try {
            tx.abort();
          } catch {
            /* Already committed. */
          }
        };
        const finish = () => {
          signal?.removeEventListener("abort", abort);
        };
        tx.oncomplete = () => {
          finish();
          resolve(result);
        };
        tx.onabort = () => {
          finish();
          reject(
            signal?.aborted
              ? new DOMException("Cancelled", "AbortError")
              : tx.error || new Error("Local storage failed."),
          );
        };
        tx.onerror = () => {}; // The transaction's abort event owns failure handling.
        signal?.addEventListener("abort", abort, { once: true });
        try {
          action(store, (value) => {
            result = value;
          });
        } catch (error) {
          abort();
          reject(error);
        }
      });
    } finally {
      db.close();
    }
  }
  info() {
    return this.transact("readonly", (store, done) => {
      store.get("info").onsuccess = (event) =>
        done(event.target.result || null);
    });
  }
  async load() {
    const value = await this.transact("readonly", (store, done) => {
      store.get("latest").onsuccess = (event) =>
        done(event.target.result || null);
    });
    if (
      value &&
      (value.schema !== "saved-local-reading-v1" ||
        !(value.result?.samples instanceof Float64Array) ||
        !value.result?.evidence ||
        !(value.original?.blob instanceof Blob))
    )
      throw new Error(
        "The saved reading could not be opened. Delete it and choose your recording again.",
      );
    return value;
  }
  save(result, original, signal) {
    const info = {
      name: result.name,
      saved_at: new Date().toISOString(),
      duration: result.evidence.audio.duration,
      model: result.evidence.model,
    };
    return this.transact(
      "readwrite",
      (store) => {
        store.put(
          {
            schema: "saved-local-reading-v1",
            result,
            original: { blob: original.blob, name: original.name },
            info,
          },
          "latest",
        );
        store.put(info, "info");
      },
      signal,
    );
  }
  delete() {
    return this.transact("readwrite", (store) => {
      store.delete("latest");
      store.delete("info");
    });
  }
}
