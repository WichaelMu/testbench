#include <gtkmm.h>

void on_button_clicked()
{
  std::cout << "Hello World" << std::endl;
}

class some_class
{
public:
  some_class
  {
    button.signal_clicked().connect(sigc::ptr_fun(&on_button_clicked));
  }
private:
  Gtk::Button button {"Hello World"};
};
