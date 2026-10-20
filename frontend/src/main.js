import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import { lengthFeedback } from './directives/lengthFeedback.js'

createApp(App)
.use(router)
.directive('length-feedback', lengthFeedback)
.mount('#app')
