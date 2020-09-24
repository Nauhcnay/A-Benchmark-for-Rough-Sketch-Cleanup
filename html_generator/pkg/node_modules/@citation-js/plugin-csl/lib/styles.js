"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.templates = exports.default = void 0;

var _core = require("@citation-js/core");

var _styles = _interopRequireDefault(require("./styles.json"));

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const templates = new _core.util.Register(_styles.default);
exports.templates = templates;

const fetchStyle = style => {
  if (templates.has(style)) {
    return templates.get(style);
  } else {
    return templates.get('apa');
  }
};

var _default = fetchStyle;
exports.default = _default;