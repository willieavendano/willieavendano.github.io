// Qlass integration config. When a class exists in Qlass, set its classUrl
// here — every "Open in Qlass" button lights up from this file.
// Note: class.avendano.xyz is THIS site's domain (GitHub Pages CNAME);
// the Qlass app lives at its own URL (Railway). Update base if that moves.
window.QLASS = {
  base: 'https://qlass-production.up.railway.app',
  courses: {
    'ap-statistics':                  { name: 'AP Statistics',                  tag: 'AP · Mathematics',       classUrl: null },
    'physics':                        { name: 'Physics',                        tag: 'Science',                classUrl: null },
    'engineering-fundamentals':       { name: 'Engineering Fundamentals',       tag: 'PLTW · Engineering',     classUrl: null },
    'intro-to-engineering-design':    { name: 'Introduction to Engineering Design', tag: 'PLTW · Engineering', classUrl: null },
    'principles-of-engineering':      { name: 'Principles of Engineering',      tag: 'PLTW · Engineering',     classUrl: null },
    'computer-science-math':          { name: 'Computer Science Math',          tag: 'Computer Science',       classUrl: null },
    'ap-research':                    { name: 'AP Research',                    tag: 'AP Capstone',            classUrl: null },
    'ap-physics-c':                   { name: 'AP Physics C',                   tag: 'AP · Science',           classUrl: null },
    'ap-computer-science-principles': { name: 'AP Computer Science Principles', tag: 'AP · Computer Science',  classUrl: null },
    'ap-computer-science-a':          { name: 'AP Computer Science A',          tag: 'AP · Computer Science',  classUrl: null }
  }
};
