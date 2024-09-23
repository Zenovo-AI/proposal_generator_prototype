{ pkgs }: {
  deps = [
    pkgs.streamlit
    pkgs.openssh
    pkgs.bash
    pkgs.postgresql
    pkgs.python3Packages.pdfplumber
    pkgs.python3Packages.beautifulsoup4  # Added BeautifulSoup
    pkgs.python3Packages.pip
    pkgs.python3Packages.requests  # Example additional dependency
    pkgs.python3Packages.trafilatura  # Added Trafilatura
  ];
}
