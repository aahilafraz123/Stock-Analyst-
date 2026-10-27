/** Minimal stand-in for the browser EventSource, driven by tests via `emit`. */
export class FakeEventSource {
  static instances = []

  static reset() {
    FakeEventSource.instances = []
  }

  static get last() {
    return FakeEventSource.instances.at(-1)
  }

  constructor(url) {
    this.url = url
    this.closed = false
    this.listeners = {}
    FakeEventSource.instances.push(this)
  }

  addEventListener(type, listener) {
    ;(this.listeners[type] ||= new Set()).add(listener)
  }

  removeEventListener(type, listener) {
    this.listeners[type]?.delete(listener)
  }

  close() {
    this.closed = true
  }

  /** Server-sent named event with a JSON body. */
  emit(type, data) {
    const event = new MessageEvent(type, { data: JSON.stringify(data) })
    this.listeners[type]?.forEach((listener) => listener(event))
  }

  /** Browser-level connection error (no data). */
  fail() {
    const event = new Event('error')
    this.listeners.error?.forEach((listener) => listener(event))
  }
}
