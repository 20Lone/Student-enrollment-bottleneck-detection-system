from app import create_app

# Create the application using our factory function
app = create_app()

if __name__ == '__main__':
    # Run the server in debug mode so it auto-reloads when you make changes
    app.run(debug=True, port=5000, threaded=True)