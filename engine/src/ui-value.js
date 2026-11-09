// Replacing unchanged text/HTML still allocates DOM nodes. Avoid doing it 20Hz.
export function updateText(node,value){const text=String(value);if(node.textContent===text)return false;node.textContent=text;return true;}
export function updateHTML(node,value){if(node.innerHTML===value)return false;node.innerHTML=value;return true;}
