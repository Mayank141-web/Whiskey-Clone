# Homebrew formula for Beer.
#
#   brew tap mayank141-web/whiskey-clone https://github.com/Mayank141-web/Whiskey-Clone
#   brew install beer
#   beer install-wine
class Beer < Formula
  desc "Run Windows apps and games (like Pokemon fan games) on macOS and Linux via Wine"
  homepage "https://github.com/Mayank141-web/Whiskey-Clone"
  url "https://github.com/Mayank141-web/Whiskey-Clone.git",
      tag: "v1.0.0"
  license "MIT"
  head "https://github.com/Mayank141-web/Whiskey-Clone.git", branch: "main"

  depends_on "python-tk@3.13"
  depends_on "python@3.13"

  def install
    libexec.install "beer"
    python = Formula["python@3.13"].opt_bin/"python3.13"
    (bin/"beer").write <<~SH
      #!/bin/sh
      PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}" exec "#{python}" -m beer "$@"
    SH
  end

  def caveats
    <<~EOS
      Finish setting up Beer with:
        beer install-wine     # downloads Wine (and Rosetta 2 on Apple Silicon)
        beer shortcut         # adds Beer.app to ~/Applications

      Then open Beer from Launchpad/Applications, or play a Pokemon fan game with:
        beer pokemon ~/Downloads/YourGame.zip
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/beer --version")
    ENV["BEER_HOME"] = testpath/"home"
    system bin/"beer", "bottle", "create", "Test", "--no-init"
    assert_path_exists testpath/"home/Bottles/Test/bottle.json"
  end
end
