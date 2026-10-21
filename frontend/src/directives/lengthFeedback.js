const fields = new WeakMap()
let nextId = 0

export const lengthFeedback = {
  mounted(el) {
    const message = document.createElement('small')
    message.id = `length-feedback-${++nextId}`
    message.className = 'length-feedback'
    message.setAttribute('role', 'status')
    message.setAttribute('aria-live', 'polite')
    message.hidden = true
    el.after(message)
    const state = { message, touched: false, attempted: false, value: el.value, invalid: false }
    const limits = () => ({ min: Number(el.getAttribute('minlength')) || 0, max: el.hasAttribute('maxlength') ? Number(el.getAttribute('maxlength')) : Infinity })
    const describe = (visible) => {
      const ids = (el.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== message.id)
      if (visible) ids.push(message.id)
      if (ids.length) el.setAttribute('aria-describedby', ids.join(' '))
      else el.removeAttribute('aria-describedby')
    }
    const render = () => {
      const { min, max } = limits()
      const length = el.value.length
      let text = ''
      let invalid = false
      if (!el.disabled && !el.readOnly) {
        if (length > max) {
          text = `Maximum length is ${max} characters. Remove ${length - max} character(s).`
          invalid = true
        } else if (Number.isFinite(max) && (state.attempted || (state.touched && length === max))) {
          text = `Maximum length is ${max} characters. No more characters can be entered.`
        } else if (state.touched && length < min && (length > 0 || el.required)) {
          text = `Enter at least ${min} characters; currently ${length}.`
          invalid = true
        }
      }
      message.textContent = text
      message.hidden = !text
      describe(Boolean(text))
      if (invalid && !state.invalid) {
        state.previousInvalid = el.getAttribute('aria-invalid')
        el.setAttribute('aria-invalid', 'true')
      } else if (!invalid && state.invalid) {
        if (state.previousInvalid === null) el.removeAttribute('aria-invalid')
        else el.setAttribute('aria-invalid', state.previousInvalid)
      }
      state.invalid = invalid
      state.value = el.value
    }
    const attemptedInsertion = (text) => {
      if (text == null || el.disabled || el.readOnly) return
      const selected = (el.selectionEnd ?? el.value.length) - (el.selectionStart ?? el.value.length)
      if (el.value.length - selected + text.length > limits().max) {
        state.attempted = true
        render()
      }
    }
    const handlers = {
      beforeinput: event => { if (!event.isComposing && event.inputType?.startsWith('insert')) attemptedInsertion(event.data) },
      paste: event => attemptedInsertion(event.clipboardData?.getData('text/plain')),
      input: event => {
        if (event.isComposing) return
        state.touched = true
        // Native maxlength may truncate typing or paste before the input event.
        if (el.value.length < limits().max) state.attempted = false
        render()
      },
      compositionend: () => { state.touched = true; state.attempted = false; render() },
      blur: () => { state.touched = true; render() },
      invalid: () => { state.touched = true; render() },
    }
    state.handlers = handlers
    state.render = render
    for (const [type, handler] of Object.entries(handlers)) el.addEventListener(type, handler)
    fields.set(el, state)
  },
  updated(el) {
    const state = fields.get(el)
    if (!state) return
    if (state.value !== el.value) {
      state.touched = false
      state.attempted = false
    }
    state.render()
  },
  beforeUnmount(el) {
    const state = fields.get(el)
    if (!state) return
    for (const [type, handler] of Object.entries(state.handlers)) el.removeEventListener(type, handler)
  },
  unmounted(el) {
    // Vue may use the next sibling as an anchor while replacing this field.
    // Remove our message only after Vue has completed that DOM update.
    fields.get(el)?.message.remove()
    fields.delete(el)
  },
}
