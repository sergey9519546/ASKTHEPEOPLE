/**
 * Temporarily store files and requirements to be uploaded
 * Used for immediate navigation after clicking start on the home page,
 * API calls are then made on the Process page.
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  usePolicyAcknowledged: false,
  projectName: '',
  additionalContext: '',
  isPending: false
})

export function setPendingUpload(
  files,
  requirement,
  usePolicyAcknowledged = false,
  projectName = '',
  additionalContext = '',
) {
  state.files = files
  state.simulationRequirement = requirement
  state.usePolicyAcknowledged = usePolicyAcknowledged
  state.projectName = projectName
  state.additionalContext = additionalContext
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    usePolicyAcknowledged: state.usePolicyAcknowledged,
    projectName: state.projectName,
    additionalContext: state.additionalContext,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.usePolicyAcknowledged = false
  state.projectName = ''
  state.additionalContext = ''
  state.isPending = false
}

export default state
