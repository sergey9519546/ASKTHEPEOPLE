# Step5Interaction.vue Refactoring Plan

## Current State (VERIFIED)
- **Total Lines**: 3,260
- **Template**: ~657 lines
- **Script**: ~703 lines  
- **Style**: ~1,805 lines

## Target Architecture

### New Sub-Components Created
1. ✅ `ChatInterface.vue` (222 lines) - Chat UI with composable
2. ✅ `SyntheticProfiles.vue` (285 lines) - Profile display with composable

### Additional Components to Create
3. `GroupResponsesPanel.vue` - Group questions/responses display
4. `OpinionMapView.vue` - Opinion map visualization wrapper
5. `ReportExplanation.vue` - Report agent chat wrapper
6. `InteractionTabs.vue` - Tab navigation component

### Composables Already Available
- ✅ `useChatConversation.js` - Chat state management
- ✅ `useSyntheticProfiles.js` - Profile loading
- ✅ `useRunStatus.js` - Live polling
- ✅ `useWorkspaceLoader.js` - Coordinated data loading

## Refactoring Strategy

### Phase 1: Extract Tab Logic (Target: -200 lines)
- Create `useInteractionTabs.js` composable
- Move tab selection logic from script section
- Extract mode guide state management

### Phase 2: Extract Chat Logic (Target: -150 lines)  
- Replace inline chat code with `ChatInterface` component
- Use existing `useChatConversation` composable
- Remove duplicate message handling

### Phase 3: Extract Profile Logic (Target: -100 lines)
- Replace inline profile code with `SyntheticProfiles` component
- Use existing `useSyntheticProfiles` composable
- Remove duplicate loading states

### Phase 4: Create Missing Components (Target: -150 lines)
- Build `GroupResponsesPanel` for group questions
- Build `OpinionMapView` for opinion map
- Build `ReportExplanation` for report agent

### Phase 5: Consolidate Styles (Target: -300 lines)
- Move shared styles to global CSS variables
- Extract common patterns (buttons, cards, tabs)
- Remove duplicate media queries

## Expected Results
- **Before**: 3,260 lines
- **After**: ~800-900 lines (-73% reduction)
- **Maintainability**: Significantly improved
- **Reusability**: High (components usable elsewhere)
- **Testability**: Much improved (isolated logic)

## Implementation Order
1. Create missing sub-components
2. Create tab management composable
3. Update Step5Interaction.vue to use new components
4. Remove duplicated code
5. Verify build passes
6. Run tests
