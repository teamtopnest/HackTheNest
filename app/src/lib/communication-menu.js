import menu from './communication-menu.json' with { type: 'json' };

export const COMMUNICATION_MENU = menu;

export function getFlashingRounds(menu) {
  return menu.children.some((item) => item.children) ? 4 : 5;
}

export function getMenuPath(menu, target, path = []) {
  if (menu === target) return path;
  for (const [index, child] of (menu.children || []).entries()) {
    const result = getMenuPath(child, target, [...path, index]);
    if (result) return result;
  }
  return null;
}
