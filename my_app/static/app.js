const data = [
  { language: "Python", usage: .10, info: "Python is a popular language for scientific computing and data analysis" },
  { language: "Java", usage: .20, info: "Java is a popular language for enterprise applications and Android development" },
  { language: "C++", usage: .08, info: "C++ is a powerful language often used for system-level programming" },
  { language: "PHP", usage: .05, info: "PHP is a popular language for web development, especially for WordPress sites" },
  { language: "TypeScript", usage: .03, info: "TypeScript is a superset of JavaScript that adds static typing" },
  { language: "Ruby", usage: .02, info: "Ruby is a dynamic, open source programming language with a focus on simplicity and productivity." },
  { language: "Swift", usage: .04, info: "Swift is a powerful and intuitive programming language for macOS, iOS, watchOS, and tvOS." },
  { language: "Kotlin", usage: .06, info: "Kotlin is a modern programming language for Android app development, and is also used in server-side and web development." },
  { language: "Go", usage: .07, info: "Go is an open source programming language developed by Google, known for its simplicity, efficiency, and scalability." },
  { language: "JavaScript", usage: .35, info: "JavaScript is the most popular programming language in the world" }
];


    const chartDiv = d3.select("#chart");
    const margin = { top: 20, right: 20, bottom: 50, left: 40 };
    const width = 960 - margin.left - margin.right;
    const height = 500 - margin.top - margin.bottom;

    const x = d3.scaleBand().rangeRound([0, width]).padding(0.1);
    const y = d3.scaleLinear().rangeRound([height, 0]);

    const svg = chartDiv.append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    x.domain(data.map(d => d.language));
    y.domain([0, d3.max(data, d => d.usage)]);

    svg.append("g")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x));

    svg.append("g")
      .call(d3.axisLeft(y).ticks(10, "%"));

    const bars = svg.selectAll(".bar")
      .data(data)
      .enter().append("rect")
      .attr("class", "bar")
      .attr("x", d => x(d.language))
      .attr("y", d => y(d.usage))
      .attr("width", x.bandwidth())
      .attr("height", d => height - y(d.usage))
      .attr("fill", "#007bff");

      bars.on("click", function (event, d) {
      // Toggle the color of the clicked bar
      const currentColor = d3.select(this).attr("fill");
      d3.select(this).attr("fill", currentColor === "black" ? "#007bff" : "black");

      // Remove any existing info elements
      svg.selectAll(".info-box").remove();

      // If the bar color is not orange, don't show the info box
      if (currentColor === "orange") {
        return;
      }

      // Calculate the x and y position of the info box
      // const xPos = x(d.language) + x.bandwidth() / 2;
      const xPos = Math.min(x(d.language) + x.bandwidth() / 2, chartWidth - 100);

      const yPos = y(d.usage) - 10;

      // Add a foreignObject to contain the HTML div element
      const foreignObject = svg.append("foreignObject")
        .attr("class", "info-box")
        .attr("x", xPos)
        .attr("y", yPos)
        .attr("width", 200)
        .attr("height", 100);

      // Add a div element inside the foreignObject
      const infoDiv = foreignObject.append("xhtml:div")
        .style("white-space", "normal")
        .style("text-align", "center")
        .text(d.info);
    });

    function renderChart() {
      // Remove any existing chart before rendering a new one
      d3.select("#chart").select("svg").remove();
    
      // Get the container width and set the chart's width and height accordingly
      const containerWidth = document.getElementById("chart").clientWidth;
      const chartWidth = containerWidth - margin.left - margin.right;
      const chartHeight = Math.min(500, containerWidth) - margin.top - margin.bottom;
    
      // Update the x and y scales
      x.rangeRound([0, chartWidth]);
      y.rangeRound([chartHeight, 0]);
    
      // Create the chart
      const svg = chartDiv.append("svg")
        .attr("width", chartWidth + margin.left + margin.right)
        .attr("height", chartHeight + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    
      // Update the domain for x and y scales
      x.domain(data.map(d => d.language));
      y.domain([0, .35]);
    
      // Add the x-axis and y-axis
      svg.append("g")
        .attr("transform", "translate(0," + chartHeight + ")")
        .call(d3.axisBottom(x));
    
      svg.append("g")
        .call(d3.axisLeft(y).ticks(10, ".0%"));
    
      // Add the bars
      const bars = svg.selectAll(".bar")
        .data(data)
        .enter().append("rect")
        .attr("class", "bar")
        .attr("x", d => x(d.language))
        .attr("y", d => y(d.usage))
        .attr("width", x.bandwidth())
        .attr("height", d => chartHeight - y(d.usage))
        .attr("fill", "#007bff");
    
      bars.on("click", function (event, d) {
        // Change the color of the clicked bar
        d3.select(this).attr("fill", "black");
    
        // Remove any existing info elements
        svg.selectAll(".info-box").remove();
    
        // Calculate the x and y position of the info box
        const xPos = Math.min(x(d.language) + x.bandwidth() / 2, chartWidth - 200);
        const yPos = y(d.usage) - 20;
    
        // Add a foreignObject to contain the HTML div element
        const foreignObject = svg.append("foreignObject")
          .attr("class", "info-box")
          .attr("x", xPos)
          .attr("y", yPos)
          .attr("width", 200)
          .attr("height", 80);
    
        // Add a div element inside the foreignObject
        const infoDiv = foreignObject.append("xhtml:div")
          .style("white-space", "normal")
          .style("text-align", "center")
          .text(d.info);
      });
    }
    

// Render the chart initially
renderChart();

// Add an event listener to update the chart on window resize
window.addEventListener("resize", renderChart);