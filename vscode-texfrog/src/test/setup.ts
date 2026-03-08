// Register a mock for the 'vscode' module before any test imports.
import Module from "node:module";

const originalResolveFilename = (Module as any)._resolveFilename;
(Module as any)._resolveFilename = function (
  request: string,
  parent: any,
  isMain: boolean,
  options: any
) {
  if (request === "vscode") {
    return require.resolve("./__mocks__/vscode");
  }
  return originalResolveFilename.call(this, request, parent, isMain, options);
};
