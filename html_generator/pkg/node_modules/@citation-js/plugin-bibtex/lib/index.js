"use strict";

var _core = require("@citation-js/core");

var _input = require("./input/");

var _output = _interopRequireDefault(require("./output/"));

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

_core.plugins.add(_input.ref, {
  input: _input.formats,
  output: _output.default
});