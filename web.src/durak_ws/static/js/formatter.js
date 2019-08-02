/*!
 * Copyright 2019 Stan Livitski
 * 
 * Licensed under the Apache License, Version 2.0 with modifications
 * and the "Commons Clause" Condition, (the "License"); you may not
 * use this file except in compliance with the License. You may obtain
 * a copy of the License at
 * 
 *  https://raw.githubusercontent.com/StanLivitski/cards.webapp/master/LICENSE
 * 
 * The grant of rights under the License will not include, and the License
 * does not grant to you, the right to Sell the Software, or use it for
 * gambling, with the exception of certain additions or modifications
 * to the Software submitted to the Licensor by third parties.
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
var Formatter;
if (Formatter !== undefined)
	throw 'Formatter constructor "Formatter" already has a value: ' + Formatter;
Formatter = function (format)
{
	if (!(this instanceof Formatter))
		return new Formatter(format);
	if (format === null)
		format = undefined;
	switch(typeof format)
	{
	case "string":
		// TODO: create the format array by finding successive matches of
		//       generalized format specifier regexp within the argument: (/.../g).exec(format) ...
		//		 see <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/RegExp/exec>
		throw 'String arguments are not yet implemented by Formatter';
	case "undefined":
		throw 'Formatter constructor requires an argument, but none is defined';
	case "object":
		if (!Array.prototype.isPrototypeOf(format))
			throw 'Unknown object type of the Formatter argument: ' + format.constructor.name
				+ '; Array expected';
		this._ = format;
		break;
	default:
		throw 'Unknown type of the Formatter argument: ' + typeof format;
	}
}
Formatter.prototype.format = function()
{
	var argIndex = 0;
	var str = '';
	var i, argIndLength;
	function $(args)
	{
		if (args.length <= argIndex)
			throw 'Formatter pattern #' + i
				+ ' references missing argument #' + (argIndex + 1)
				+ '. The number of arguments was: ' + args.length;
		var arg = args[argIndex];
		if (0 > argIndLength)
			argIndex++;
		return arg;
	}
	for(i=0; i<this._.length; i++)
	{
		var pattern = this._[i];
		if (typeof pattern != 'string')
			throw 'Type of a Formatter pattern #' + i + ', expected string, got: ' + typeof pattern;
		else if (pattern.charAt(0) != '%')
		{
			str += pattern;
			continue;
		}
		pattern = pattern.substring(1);
		argIndLength = pattern.indexOf('$');
		if (0 <= argIndLength)
		{
			var val = parseInt(pattern.substring(0, argIndLength));
			if (isNaN(val))
				throw 'Invalid Formatter pattern #' + i + ': %' + pattern;
			argIndex = val - 1;
			pattern = pattern.substring(argIndLength + 1);
		}
		// TODO: [flags][width][.precision]
		switch(pattern)
		{
		case '%':
			str += '%'
			break;
		case 'n':
			str += '\n';
			break;
		case 'd':
			var arg = $(arguments);
			if (typeof arg != 'number')
				throw 'Formatter pattern #' + i + ' (%' + pattern
				+ ') requires a numeric argument #' + (argIndex + (0 > argIndLength ? 0 : 1))
				+ '. The actual argument was: ' + arg;
			str += arg.toString();
			break;
		case 'f':
			var arg = $(arguments);
			if (typeof arg != 'number')
				throw 'Formatter pattern #' + i + ' (%' + pattern
				+ ') requires a numeric argument #' + (argIndex + (0 > argIndLength ? 0 : 1))
				+ '. The actual argument was: ' + arg;
			str += arg.toFixed();
			break;
		case 'e':
		case 'E':
			var arg = $(arguments);
			if (typeof arg != 'number')
				throw 'Formatter pattern #' + i + ' (%' + pattern
				+ ') requires a numeric argument #' + (argIndex + (0 > argIndLength ? 0 : 1))
				+ '. The actual argument was: ' + arg;
			str += arg.toExponential();
			break;
		case 'x':
		case 'X':
			var arg = $(arguments);
			if (typeof arg != 'number')
				throw 'Formatter pattern #' + i + ' (%' + pattern
				+ ') requires a numeric argument #' + (argIndex + (0 > argIndLength ? 0 : 1))
				+ '. The actual argument was: ' + arg;
			arg = arg.toString(16);
			if (pattern == 'X')
				arg = arg.toUpperCase();
			str += arg;
			break;
		case 'o':
			var arg = $(arguments);
			if (typeof arg != 'number')
				throw 'Formatter pattern #' + i + ' (%' + pattern
				+ ') requires a numeric argument #' + (argIndex + (0 > argIndLength ? 0 : 1))
				+ '. The actual argument was: ' + arg;
			str += arg.toString(8);
			break;
		case 's':
			var arg = $(arguments);
			if (arg == null)
				str += 'null';
			else if (typeof arg == 'string')
				str += arg;
			else
				str += String(arg);
			break;
		default:
			throw 'Invalid or unsupported conversion in Formatter pattern #' + i + ': %' + pattern;
		}
	}
	return str;
}

