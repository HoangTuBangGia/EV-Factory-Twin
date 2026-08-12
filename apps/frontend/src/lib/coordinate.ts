export const FACTORY_SIZE = { width: 20, height: 15 };

export function worldToScreen(
  x: number, y: number, factoryWidth: number, factoryHeight: number,
  screenWidth: number, screenHeight: number,
) {
  return { x: (x / factoryWidth) * screenWidth, y: screenHeight - (y / factoryHeight) * screenHeight };
}
