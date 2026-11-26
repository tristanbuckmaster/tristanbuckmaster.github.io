require 'bibtex'
require 'cgi'
require 'mini_racer'

module BibTeX
  module Filters
    # Keep the source BibTeX intact. Convert math only in the HTML rendition.
    class PlatesBibliography < Filter
      FORMULA = /(?<!\\)\$\$(.+?)(?<!\\)\$\$|(?<!\\)\$(.+?)(?<!\\)\$|\\\((.+?)\\\)|\\\[(.+?)\\\]/m.freeze

      def apply(value)
        formulas = []
        protected_text = value.to_s.gsub(FORMULA) do
          display, inline, parenthesized, bracketed = Regexp.last_match.captures
          tex = display || inline || parenthesized || bracketed
          formulas << render_formula(tex, !!(display || bracketed))
          "\uE000#{formulas.length - 1}\uE001"
        end
        # Jekyll-Scholar's default decoder handles accents and BibTeX case braces.
        protected_text = protected_text.gsub(/\{\\em\s+([^{}]+)\}/, '<em>\1</em>')
        ::LaTeX.decode(protected_text).gsub(/\uE000(\d+)\uE001/) { formulas[Regexp.last_match(1).to_i] }
      end

      private

      def render_formula(tex, display)
        @formulas ||= {}
        @formulas[[tex, display]] ||= renderer.call('renderFormula', tex, display)
      rescue MiniRacer::RuntimeError => error
        Jekyll.logger.warn('Bibliography math:', "#{tex.inspect}: #{error.message}")
        "<code>#{CGI.escapeHTML(tex)}</code>"
      end

      def renderer
        @renderer ||= begin
          context = MiniRacer::Context.new
          # https://www.npmjs.com/package/temml/v/0.14.0 (MIT, license alongside the renderer)
          context.eval(File.read(File.join(__dir__, 'temml-0.14.0', 'temml.min.js')))
          context.eval('function renderFormula(tex, displayMode) { return temml.renderToString(tex, {displayMode, throwOnError: true}); }')
          context
        end
      end
    end
  end
end
