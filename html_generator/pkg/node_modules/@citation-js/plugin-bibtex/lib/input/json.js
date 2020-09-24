"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = exports.parse = void 0;

var _prop = _interopRequireDefault(require("./prop"));

var _type = _interopRequireDefault(require("./type"));

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const parseBibTeXJSON = function (data) {
  return [].concat(data).map(entry => {
    const newEntry = {};
    let toMerge = [];

    for (let prop in entry.properties) {
      const oldValue = entry.properties[prop];
      const [cslField, cslValue] = (0, _prop.default)(prop, oldValue) || [];

      if (cslField) {
        if (/^[^:\s]+?:[^.\s]+(\.[^.\s]+)*$/.test(cslField)) {
          toMerge.push([cslField, cslValue]);
        } else {
          newEntry[cslField] = cslValue;
        }
      }
    }

    newEntry.type = (0, _type.default)(entry.type);
    newEntry.id = newEntry['citation-label'] = entry.label;

    if (/\d(\D+)$/.test(entry.label)) {
      newEntry['year-suffix'] = entry.label.match(/\d(\D+)$/)[1];
    }

    toMerge.forEach(([cslField, value]) => {
      const props = cslField.split(/:|\./g);
      let cursor = newEntry;

      while (props.length > 0) {
        const prop = props.shift();
        cursor = cursor[prop] || (cursor[prop] = !props.length ? value : isNaN(+props[0]) ? {} : []);
      }
    });
    return newEntry;
  });
};

exports.default = exports.parse = parseBibTeXJSON;