/* Flowers: what the game page shows for this feature. */
// A stationary mouse is still contact. Camera samples must keep arriving themselves.
DotdewPages.every(100, ()=>{
 if(!detailMode && mouseContact && pointerInside && currentState?.page==='flower_detail' && currentState.flowers?.watering && !currentState.paused && !document.hidden && document.hasFocus())
  queuePointer('/api/pointer/move',pointerX,pointerY);
});
