<script setup>
import { apiBaseUrl, apiFetch } from '../api.js'
import { computed, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'


const step = ref(1)
const weightErrors = reactive({})
const saving = ref(false)
const error = ref('')
const createdTemplate = ref(null)
const draft = reactive({
  title: '',
  description: '',
  criteria: [{ id: crypto.randomUUID(), name: '', weight: 1 }],
  items: [{ id: crypto.randomUUID(), name: '', image: null, imageUrl: '' }],
})

const steps = ['Template details', 'Rating criteria', 'Items to rate']
const readyToSave = computed(() => draft.items.length > 0 && draft.items.every(item => item.name.trim() && item.image))

function addCriterion() {
  draft.criteria.push({ id: crypto.randomUUID(), name: '', weight: 1 })
}

function removeCriterion(id) {
  draft.criteria = draft.criteria.filter(item => item.id !== id)
  delete weightErrors[id]
}

function updateWeight(criterion, event) {
  const value = event.target.value
  if (!/^\d*$/.test(value)) {
    event.target.value = String(criterion.weight)
    weightErrors[criterion.id] = 'Use a whole number from 1 to 10. Decimals are not allowed.'
    return
  }
  criterion.weight = value === '' ? '' : Number(value)
  weightErrors[criterion.id] = Number.isInteger(criterion.weight) && criterion.weight >= 1 && criterion.weight <= 10
    ? '' : 'Enter a whole number from 1 to 10.'
}

function validateCriteria() {
  if (!draft.criteria.length || draft.criteria.some(item => !item.name.trim())) {
    error.value = 'Add at least one named rating criterion.'
    return false
  }
  if (draft.criteria.some(item => weightErrors[item.id] || !Number.isInteger(item.weight) || item.weight < 1 || item.weight > 10)) {
    error.value = 'Every weight must be a whole number from 1 to 10.'
    return false
  }
  return true
}

function goBack(targetStep) {
  if (saving.value || createdTemplate.value || targetStep < 1 || targetStep >= step.value) return
  error.value = ''
  step.value = targetStep
}

function addItem() {
  draft.items.push({ id: crypto.randomUUID(), name: '', image: null, imageUrl: '' })
}

function removeItem(id) {
  const item = draft.items.find(entry => entry.id === id)
  if (item?.imageUrl) URL.revokeObjectURL(item.imageUrl)
  draft.items = draft.items.filter(entry => entry.id !== id)
}

function selectImage(item, event) {
  const file = event.target.files?.[0]
  if (!file) return
  error.value = ''
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'Each image must be 5 MB or smaller.'
    event.target.value = ''
    return
  }
  if (item.imageUrl) URL.revokeObjectURL(item.imageUrl)
  item.image = file
  item.imageUrl = URL.createObjectURL(file)
}

function continueToCriteria() {
  error.value = ''
  if (!draft.title.trim()) {
    error.value = 'Enter a template name before continuing.'
    return
  }
  step.value = 2
}

function confirmCriteria() {
  error.value = ''
  if (!validateCriteria()) return
  step.value = 3
}

async function saveTemplate() {
  if (saving.value || createdTemplate.value) return
  error.value = ''
  if (!draft.title.trim()) {
    step.value = 1
    error.value = 'Enter a template name before saving.'
    return
  }
  if (!validateCriteria()) {
    step.value = 2
    return
  }
  if (!readyToSave.value) {
    error.value = 'Every item needs both a name and an image.'
    return
  }

  const formData = new FormData()
  formData.append('title', draft.title.trim())
  formData.append('description', draft.description.trim())
  formData.append('criteria', JSON.stringify(
    draft.criteria.map(({ name, weight }) => ({ name: name.trim(), weight })),
  ))
  formData.append('items', JSON.stringify(
    draft.items.map(({ name }) => ({ name: name.trim() })),
  ))
  draft.items.forEach((item, index) => formData.append(`item_image_${index}`, item.image))

  saving.value = true
  try {
    const response = await apiFetch(`${apiBaseUrl}/api/templates/`, {
      method: 'POST',
      body: formData,
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to create the template.')
    createdTemplate.value = data
  } catch (requestError) {
    error.value = requestError.message || 'Unable to connect to the server.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="editor-heading">
      <div>
        <div class="eyebrow">YOUR RATING WORKSPACE</div>
        <h1>Create a template</h1>
        <p>Define the template first. Rating and ranking happen after it has been saved.</p>
      </div>
    </div>

    <div class="editor-top">
      <span class="state-badge">New template</span>
      <span class="save-status">{{ createdTemplate ? 'Saved' : 'Not saved' }}</span>
    </div>

    <div class="editor-steps" aria-label="Template creation steps">
      <button v-for="(label, index) in steps" :key="label" type="button" :aria-current="step === index + 1 ? 'step' : undefined" :disabled="index + 1 >= step || saving || Boolean(createdTemplate)" @click="goBack(index + 1)">
        <span>{{ index + 1 }}</span>{{ label }}
      </button>
    </div>

    <div v-if="createdTemplate" class="template-created">
      <span>✓</span>
      <h1>Template created</h1>
      <p><strong>{{ createdTemplate.title }}</strong> was saved with ID {{ createdTemplate.id }}.</p>
      <RouterLink class="action-button primary" to="/home_page">Return to Discover</RouterLink>
    </div>

    <div v-else class="editor-content">
      <template v-if="step === 1">
        <h1>Start with the template details</h1>
        <p class="editor-description">Give the template a clear name and briefly explain what it compares.</p>
        <div class="editor-basics">
          <label class="editor-field">Template name<input v-length-feedback v-model="draft.title" maxlength="120" placeholder="e.g. My favorite neighborhood cafés" required></label>
          <label class="editor-field">Description <span class="optional">Optional</span><textarea v-length-feedback v-model="draft.description" maxlength="600" rows="4" placeholder="What is this template for?" /></label>
        </div>
      </template>

      <template v-else-if="step === 2">
        <h1>Define the rating criteria</h1>
        <p class="editor-description">You can return to edit criteria before saving. Criteria are locked once the template is saved.</p>
        <div class="editor-section-heading">
          <h2>Rating criteria <span>{{ draft.criteria.length }}</span></h2>
          <button class="action-button" type="button" @click="addCriterion">+ Add criterion</button>
        </div>
        <p class="editor-hint">Weights control how strongly each criterion affects a future rating. Use whole numbers from 1 to 10.</p>
        <div class="editable-list">
          <div v-for="(criterion, index) in draft.criteria" :key="criterion.id" class="criterion-editor">
            <span class="row-number">{{ index + 1 }}</span>
            <label class="editor-field">Criterion<input v-length-feedback v-model="criterion.name" maxlength="100" placeholder="e.g. Flavor"></label>
            <label class="editor-field">Weight<input :value="criterion.weight" type="text" inputmode="numeric" pattern="[0-9]+" :aria-invalid="Boolean(weightErrors[criterion.id])" :aria-describedby="weightErrors[criterion.id] ? `weight-error-${criterion.id}` : undefined" @input="updateWeight(criterion, $event)"><small v-if="weightErrors[criterion.id]" :id="`weight-error-${criterion.id}`" class="weight-error" role="alert">{{ weightErrors[criterion.id] }}</small></label>
            <button class="remove-button" type="button" aria-label="Remove criterion" @click="removeCriterion(criterion.id)">×</button>
          </div>
        </div>
      </template>

      <template v-else>
        <h1>Add the items this template will rate</h1>
        <p class="editor-description">Each item needs a name and an image. You can add or remove items before saving.</p>
        <div class="editor-section-heading">
          <h2>Items <span>{{ draft.items.length }}</span></h2>
          <button class="action-button" type="button" @click="addItem">+ Add item</button>
        </div>
        <div class="editable-list">
          <div v-for="(item, index) in draft.items" :key="item.id" class="item-editor">
            <label class="item-image-upload">
              <img v-if="item.imageUrl" :src="item.imageUrl" alt="">
              <span v-else>{{ index + 1 }}</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" @change="selectImage(item, $event)">
            </label>
            <label class="editor-field item-fields">Item name<input v-length-feedback v-model="item.name" maxlength="120" placeholder="e.g. Corner café"></label>
            <button class="remove-button" type="button" aria-label="Remove item" @click="removeItem(item.id)">×</button>
          </div>
        </div>
      </template>

      <p v-if="error" class="template-error" role="alert">{{ error }}</p>

      <div class="editor-bottom">
        <button v-if="step > 1" class="action-button" type="button" :disabled="saving" @click="goBack(step - 1)">Back</button>
        <span v-else>Step {{ step }} of {{ steps.length }}</span>
        <button v-if="step === 1" class="action-button primary" type="button" @click="continueToCriteria">Continue</button>
        <button v-else-if="step === 2" class="action-button primary" type="button" @click="confirmCriteria">Confirm criteria</button>
        <button v-else class="action-button primary" type="button" :disabled="saving" @click="saveTemplate">{{ saving ? 'Saving…' : 'Save template' }}</button>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.editor-steps button:disabled { cursor: default; opacity: 1; }
.item-image-upload { position: relative; display: flex; flex-shrink: 0; align-items: center; justify-content: center; width: 70px; height: 70px; overflow: hidden; border-radius: 9px; background: #edf2e7; color: var(--text-secondary); cursor: pointer; }
.item-image-upload img { width: 100%; height: 100%; object-fit: cover; }
.item-image-upload input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.template-error { margin: 22px 0 0; color: #a74842; font-size: 13px; }
.weight-error { color: #a74842; font-size: 12px; font-weight: 400; }
.template-created { max-width: 680px; margin: 60px auto; padding: 54px; border: 1px solid #e3eadc; border-radius: 14px; background: #f8faf5; text-align: center; }
.template-created > span { display: flex; align-items: center; justify-content: center; width: 54px; height: 54px; margin: 0 auto 20px; border-radius: 50%; background: #dfead8; color: #325c48; font-size: 26px; }
.template-created p { margin: 14px 0 28px; color: var(--text-secondary); }
</style>
