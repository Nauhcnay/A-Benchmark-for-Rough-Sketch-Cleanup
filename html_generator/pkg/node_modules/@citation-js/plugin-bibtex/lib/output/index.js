"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;

var _core = require("@citation-js/core");

var _json = _interopRequireDefault(require("./json"));

var _text = require("./text");

var _bibtxt = require("./bibtxt");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const factory = function (formatter) {
  return function (data, opts = {}) {
    const {
      type,
      format = type || 'text'
    } = opts;

    if (format === 'object') {
      return data.map(_json.default);
    } else if (_core.plugins.dict.has(format)) {
      return formatter(data, _core.plugins.dict.get(format), opts);
    } else {
      return '';
    }
  };
};

var _default = {
  bibtex: factory(_text.getBibtex),
  bibtxt: factory(_bibtxt.getBibtxt)
};
exports.default = _default;