// main.ts — Application entry point
//
// WHAT IS AN ENTRY POINT? This is the first file that runs when the browser
// loads your app. It does three things:
// 1. Imports the global CSS (styles shared across all components)
// 2. Imports the root App component (the top-level building block)
// 3. Mounts the app into the HTML element with id="app" (in index.html)
//
// In Svelte 5, mount() replaces the old `new App()` constructor.
// The `!` after getElementById tells TypeScript "I guarantee this element exists."

import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

const app = mount(App, {
  target: document.getElementById('app')!,
})

export default app
